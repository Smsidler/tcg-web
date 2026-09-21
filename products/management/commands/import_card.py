from django.core.management.base import BaseCommand, CommandError

from products.services.tcgdex import CatalogError, import_card


class Command(BaseCommand):
    help = "Importa o actualiza una carta desde TCGdex (catálogo en inglés), sin alterar productos"

    def add_arguments(self, parser):
        parser.add_argument("card_id", help="ID TCGdex; por ejemplo: base1-4")

    def handle(self, *args, **options):
        try:
            card, created = import_card(options["card_id"])
        except CatalogError as exc:
            raise CommandError(str(exc)) from exc
        action = "importada" if created else "actualizada"
        self.stdout.write(self.style.SUCCESS(f"Carta {action}: {card.name} ({card.tcgdex_id})"))
