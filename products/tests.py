import copy
import io
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from .admin import CardAdmin, ProductAdmin
from .models import Card, Product, Set
from .services.tcgdex import CatalogError, fetch_json, import_card
from .templatetags.product_filters import clp


class ProductFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.card_set = Set.objects.create(tcgdex_id="base1", name="Base Set")
        cls.card = Card.objects.create(tcgdex_id="base1-4", local_id="4", name="Charizard", set=cls.card_set)
        cls.product = Product.objects.create(card=cls.card, price="1000.00", stock=4)


class ModelAndAdminTests(ProductFixture):
    def test_missing_image_is_safe_in_both_admins(self):
        self.assertEqual(CardAdmin(Card, AdminSite()).image_preview(self.card), "Sin imagen")
        self.assertEqual(ProductAdmin(Product, AdminSite()).image_preview(self.product), "Sin imagen")

    def test_admin_escapes_image_attributes(self):
        self.card.image = 'https://example.com/" onerror="alert(1)'
        html = str(CardAdmin(Card, AdminSite()).image_preview(self.card))
        self.assertNotIn('src="https://example.com/" onerror=', html)
        self.assertIn('&quot;', html)

    def test_prices_rejected_by_validation_and_database(self):
        self.product.price = Decimal("-1")
        with self.assertRaises(ValidationError):
            self.product.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=self.product.pk).update(price=-1)

    def test_sku_is_unique(self):
        another = Product.objects.create(card=self.card, price=100, stock=1)
        self.assertNotEqual(self.product.sku, another.sku)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(card=self.card, price=1, sku=self.product.sku)

    def test_catalog_deletion_protects_inventory(self):
        with self.assertRaises(ProtectedError):
            self.card.delete()
        with self.assertRaises(ProtectedError):
            self.card_set.delete()
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_money_does_not_truncate_cents(self):
        self.assertEqual(clp(Decimal("1234.00")), "$1.234")
        self.assertEqual(clp(Decimal("1234.50")), "$1.234,50")


@override_settings(SECURE_SSL_REDIRECT=False)
class CatalogTests(ProductFixture):
    def test_multiple_products_have_individual_details(self):
        second = Product.objects.create(card=self.card, price=2000, stock=1, variant="holo")
        for product in [self.product, second]:
            response = self.client.get(reverse("product_detail", args=[product.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, product.sku)
        response = self.client.get(reverse("legacy_card_detail", args=[self.card.tcgdex_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("product_detail", args=[second.pk]))

    def test_single_product_legacy_link_redirects(self):
        response = self.client.get(reverse("legacy_card_detail", args=[self.card.tcgdex_id]))
        self.assertRedirects(response, reverse("product_detail", args=[self.product.pk]))

    def test_orphan_and_unknown_products_are_not_exposed(self):
        orphan = Product.objects.create(price=100, stock=2)
        self.assertEqual(self.client.get(reverse("product_detail", args=[orphan.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("product_detail", args=[99999])).status_code, 404)
        self.assertEqual(self.client.get(reverse("home")).context["page_obj"].paginator.count, 1)

    def test_filters_pagination_and_order_are_preserved(self):
        for index in range(15):
            Product.objects.create(card=self.card, price=2000 + index, stock=1)
        Product.objects.create(card=self.card, price=1, stock=0)
        response = self.client.get(reverse("home"), {"q": "Charizard", "set": "base1", "in_stock": "1", "sort": "price_asc"})
        self.assertEqual(response.context["page_obj"].paginator.count, 16)
        self.assertEqual(len(response.context["products"]), 12)
        self.assertEqual(response.context["products"][0].pk, self.product.pk)
        self.assertContains(response, 'value="Charizard"')
        self.assertContains(response, 'q=Charizard&amp;set=base1&amp;in_stock=1&amp;sort=price_asc&amp;page=2')
        page_two = self.client.get(reverse("home"), {"q": "Charizard", "in_stock": "1", "page": 2})
        self.assertEqual(len(page_two.context["products"]), 4)

    def test_invalid_sort_and_page_have_safe_defaults(self):
        response = self.client.get(reverse("home"), {"sort": "bad-field", "page": "bad-page"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sort"], "newest")
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_empty_search_and_missing_images_render(self):
        self.assertContains(self.client.get(reverse("home")), "Imagen no disponible")
        self.assertContains(self.client.get(reverse("home"), {"q": "no-such-card"}), "No se encontraron productos")


@override_settings(SECURE_SSL_REDIRECT=False)
class CartTests(ProductFixture):
    def add(self, quantity=1, **kwargs):
        return self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": quantity, **kwargs})

    def test_add_update_remove_and_no_inventory_changes(self):
        self.add(2)
        self.add(1)
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 3)
        self.client.post(reverse("cart_update", args=[self.product.pk]), {"quantity": 1})
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.client.post(reverse("cart_remove", args=[self.product.pk]))
        self.assertEqual(self.client.session["cart"], {})

    def test_stock_and_quantity_validated_on_server(self):
        for quantity in [0, -1, "1.5", "invalid", 5, 10000]:
            with self.subTest(quantity=quantity):
                self.add(quantity)
                self.assertNotIn(str(self.product.pk), self.client.session.get("cart", {}))
        self.add(3)
        self.add(2)
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 3)

    def test_stock_zero_cannot_be_added(self):
        self.product.stock = 0
        self.product.save()
        self.add(1)
        self.assertFalse(self.client.session.get("cart"))

    def test_prices_are_live_and_client_price_is_ignored(self):
        self.add(2, price="0.01", subtotal="0.02")
        Product.objects.filter(pk=self.product.pk).update(price="1250.50")
        response = self.client.get(reverse("cart_detail"))
        self.assertEqual(response.context["total"], Decimal("2501.00"))
        self.assertContains(response, "$2.501")
        self.assertEqual(self.client.session["cart"], {str(self.product.pk): 2})

    def test_stock_change_warns_and_rejects_invalid_update(self):
        self.add(3)
        Product.objects.filter(pk=self.product.pk).update(stock=1)
        response = self.client.get(reverse("cart_detail"))
        self.assertContains(response, "El stock cambió")
        self.client.post(reverse("cart_update", args=[self.product.pk]), {"quantity": 2})
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 3)
        self.client.post(reverse("cart_update", args=[self.product.pk]), {"quantity": 1})
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 1)

    def test_deleted_and_unlinked_products_are_removed(self):
        self.add()
        self.product.delete()
        response = self.client.get(reverse("cart_detail"))
        self.assertContains(response, "Tu carrito está vacío")
        self.assertEqual(self.client.session["cart"], {})

    def test_cart_is_private_to_session(self):
        self.add()
        self.assertContains(Client().get(reverse("cart_detail")), "Tu carrito está vacío")

    def test_mutations_require_post_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for name in ["cart_add", "cart_update", "cart_remove"]:
            url = reverse(name, args=[self.product.pk])
            self.assertEqual(client.get(url).status_code, 405)
            self.assertEqual(client.post(url, {"quantity": 1}).status_code, 403)
        client.get(reverse("product_detail", args=[self.product.pk]))
        response = client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 1, "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 302)

    def test_corrupt_session_data_does_not_crash(self):
        session = self.client.session
        session["cart"] = {"abc": 1, "9" * 100: 1, str(self.product.pk): -2, "1": True}
        session.save()
        response = self.client.get(reverse("cart_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["cart"], {})


CARD_PAYLOAD = {
    "id": "base1-4", "localId": "4", "name": "Charizard",
    "set": {"id": "base1", "name": "Base Set updated", "logo": "https://assets.tcgdex.net/en/base/base1/logo"},
    "image": "https://assets.tcgdex.net/en/base/base1/4", "rarity": "Rare",
}


class ImportTests(ProductFixture):
    @patch("products.services.tcgdex.fetch_json")
    def test_repeat_updates_catalog_without_touching_products(self, fetch):
        fetch.return_value = copy.deepcopy(CARD_PAYLOAD)
        original_sku = self.product.sku
        import_card("base1-4")
        import_card("base1-4")
        self.assertEqual(Card.objects.count(), 1)
        self.assertEqual(Set.objects.count(), 1)
        self.card_set.refresh_from_db()
        self.assertEqual(self.card_set.name, "Base Set updated")
        self.product.refresh_from_db()
        self.assertEqual((self.product.price, self.product.stock, self.product.sku), (Decimal("1000"), 4, original_sku))
        self.assertEqual(Product.objects.count(), 1)

    @patch("products.services.tcgdex.fetch_json")
    def test_validation_happens_before_any_write(self, fetch):
        for payload in [{}, {**CARD_PAYLOAD, "id": "wrong"}, {**CARD_PAYLOAD, "localId": None}, {**CARD_PAYLOAD, "image": "javascript:alert(1)"}, {**CARD_PAYLOAD, "set": None}]:
            with self.subTest(payload=payload):
                fetch.return_value = copy.deepcopy(payload)
                with self.assertRaises(CatalogError):
                    import_card("base1-4")
        self.card_set.refresh_from_db()
        self.assertEqual(self.card_set.name, "Base Set")

    @patch("products.services.tcgdex.fetch_json", return_value=CARD_PAYLOAD)
    def test_database_failure_rolls_back_set_update(self, fetch):
        with patch("products.services.tcgdex.Card.objects.update_or_create", side_effect=IntegrityError("failure")):
            with self.assertRaises(IntegrityError):
                import_card("base1-4")
        self.card_set.refresh_from_db()
        self.assertEqual(self.card_set.name, "Base Set")

    @patch("products.services.tcgdex.fetch_json")
    def test_missing_logo_does_not_erase_existing_logo(self, fetch):
        self.card_set.logo = "https://example.com/logo"
        self.card_set.save()
        payload = copy.deepcopy(CARD_PAYLOAD)
        del payload["set"]["logo"]
        payload["image"] = None
        fetch.return_value = payload
        import_card("base1-4")
        self.card_set.refresh_from_db()
        self.assertEqual(self.card_set.logo, "https://example.com/logo")

    @patch("products.services.tcgdex.fetch_json", return_value=CARD_PAYLOAD)
    def test_set_mismatch_rejected(self, fetch):
        with self.assertRaises(CatalogError):
            import_card("base1-4", expected_set="base2")

    @patch("products.services.tcgdex.urlopen")
    def test_http_timeout_is_explicit_and_response_is_closed(self, opener):
        response = opener.return_value.__enter__.return_value
        response.read.return_value = json.dumps(CARD_PAYLOAD).encode()
        self.assertEqual(fetch_json("cards", "base1-4")["id"], "base1-4")
        self.assertEqual(opener.call_args.kwargs["timeout"], 15)
        opener.return_value.__exit__.assert_called_once()

    @patch("products.services.tcgdex.time.sleep")
    @patch("products.services.tcgdex.urlopen")
    def test_network_retries_are_bounded(self, opener, sleep):
        opener.side_effect = URLError("unavailable")
        with self.assertRaises(CatalogError):
            fetch_json("cards", "base1-4")
        self.assertEqual(opener.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("products.services.tcgdex.urlopen")
    def test_404_does_not_retry(self, opener):
        opener.side_effect = HTTPError("url", 404, "missing", {}, None)
        with self.assertRaisesMessage(CatalogError, "No existe"):
            fetch_json("cards", "missing")
        self.assertEqual(opener.call_count, 1)

    @patch("products.services.tcgdex.urlopen")
    def test_malformed_json_and_ids_are_rejected(self, opener):
        opener.return_value.__enter__.return_value.read.return_value = b"<html>error</html>"
        with self.assertRaises(CatalogError):
            fetch_json("cards", "base1-4")
        opener.reset_mock()
        with self.assertRaises(CatalogError):
            fetch_json("cards", "../sets")
        opener.assert_not_called()

    @patch("products.services.tcgdex.fetch_json")
    def test_import_set_limit_and_idempotence(self, fetch):
        set_payload = {"id": "base1", "name": "Base Set", "cards": [{"id": "base1-4"}, {"id": "base1-5"}]}
        fetch.side_effect = [set_payload, CARD_PAYLOAD, set_payload, CARD_PAYLOAD]
        for _ in range(2):
            call_command("import_set", "base1", limit=1, stdout=io.StringIO())
        self.assertEqual(Card.objects.count(), 1)
        self.assertEqual(fetch.call_count, 4)

    @patch("products.management.commands.import_set.fetch_set_cards", return_value=["base1-4", "base1-5"])
    @patch("products.management.commands.import_set.import_card")
    def test_partial_import_reports_failure_and_continues(self, importer, fetch):
        importer.side_effect = [CatalogError("failed"), (self.card, True)]
        with self.assertRaisesMessage(CommandError, "Creadas: 1; actualizadas: 0; fallidas: 1"):
            call_command("import_set", "base1", stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(importer.call_count, 2)

    def test_invalid_import_limit(self):
        with self.assertRaises(CommandError):
            call_command("import_set", "base1", limit=0)


class ExistingInventoryMigrationTests(TransactionTestCase):
    migrate_from = ("products", "0002_card_set_remove_product_name_alter_product_category_and_more")
    migrate_to = ("products", "0003_product_condition_product_language_product_sku_and_more")

    def test_existing_products_receive_distinct_skus_without_data_loss(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldProduct = old_apps.get_model("products", "Product")
        first = OldProduct.objects.create(price="1234.50", stock=7, description="Original")
        second = OldProduct.objects.create(price="500", stock=2)
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([self.migrate_to])
            first_new = Product.objects.get(pk=first.pk)
            second_new = Product.objects.get(pk=second.pk)
            self.assertTrue(first_new.sku)
            self.assertNotEqual(first_new.sku, second_new.sku)
            self.assertEqual(first_new.price, Decimal("1234.50"))
            self.assertEqual(first_new.stock, 7)
            self.assertEqual(first_new.description, "Original")
            self.assertEqual(first_new.language, "unknown")
            self.assertIsNone(first_new.card_id)
        finally:
            MigrationExecutor(connection).migrate([self.migrate_to])
