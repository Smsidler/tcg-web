import json
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from products.models import Card, Set


class Command(BaseCommand):
    help = "Importa una carta desde TCGdex"

    def add_arguments(self, parser):
        parser.add_argument(
            "card_id",
            type=str,
            help="ID de la carta en TCGdex, por ejemplo: base1-4"
        )

    def handle(self, *args, **options):
        card_id = options["card_id"]

        url = f"https://api.tcgdex.net/v2/en/cards/{card_id}"

        try:
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode())
        except Exception as e:
            raise CommandError(f"No se pudo obtener la carta: {e}")

        set_data = data["set"]

        card_set, created = Set.objects.get_or_create(
            tcgdex_id=set_data["id"],
            defaults={
                "name": set_data["name"],
                "logo": set_data.get("logo", "")
            }
        )

        card, created = Card.objects.update_or_create(
            tcgdex_id=data["id"],
            defaults={
                "local_id": data["localId"],
                "name": data["name"],
                "image": data.get("image", ""),
                "category": data.get("category", ""),
                "rarity": data.get("rarity", ""),
                "illustrator": data.get("illustrator", ""),
                "set": card_set
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Carta importada correctamente: {card.name}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Carta actualizada correctamente: {card.name}"
                )
            )