from django.core.management.base import BaseCommand, CommandError

from products.services.tcgdex import CatalogError, fetch_set_cards, import_card


class Command(BaseCommand):
    help = "Importa un set por carta; se puede repetir sin duplicados ni cambios de precio/stock"

    def add_arguments(self, parser):
        parser.add_argument("set_id", help="ID TCGdex; por ejemplo: base1")
        parser.add_argument("--limit", type=int, help="Importar solo las primeras N cartas")

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit <= 0:
            raise CommandError("--limit debe ser mayor que cero.")
        try:
            identifiers = fetch_set_cards(options["set_id"])
        except CatalogError as exc:
            raise CommandError(str(exc)) from exc
        created_count = updated_count = failed_count = 0
        for identifier in identifiers[:limit]:
            try:
                _, created = import_card(identifier, expected_set=options["set_id"])
                created_count += int(created)
                updated_count += int(not created)
            except CatalogError as exc:
                failed_count += 1
                self.stderr.write(f"{identifier}: {exc}")
        summary = f"Creadas: {created_count}; actualizadas: {updated_count}; fallidas: {failed_count}."
        if failed_count:
            raise CommandError(summary + " Las cartas correctas se conservaron; puedes repetir el comando.")
        self.stdout.write(self.style.SUCCESS(summary))
