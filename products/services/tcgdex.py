"""TCGdex catalog synchronization. This module never writes Product data."""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction

from products.models import Card, Set

BASE_URL = "https://api.tcgdex.net/v2/en"
TIMEOUT = 15
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class CatalogError(Exception):
    """An actionable remote API or catalog validation failure."""


def validate_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise CatalogError("ID inválido: usa letras, números, guiones o guiones bajos.")
    return value


def fetch_json(resource, identifier):
    validate_id(identifier)
    if resource not in {"cards", "sets"}:
        raise CatalogError("Recurso de catálogo no permitido.")
    request = Request(f"{BASE_URL}/{resource}/{identifier}", headers={"Accept": "application/json"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=TIMEOUT) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise CatalogError("La respuesta del catálogo excede el tamaño permitido.")
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict):
                raise CatalogError("TCGdex no devolvió un objeto JSON.")
            return data
        except HTTPError as exc:
            if exc.code == 404:
                raise CatalogError(f"No existe {resource}/{identifier} en TCGdex (en).") from exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise CatalogError(f"TCGdex respondió HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            if attempt == 2:
                raise CatalogError("No se pudo conectar con TCGdex después de 3 intentos.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CatalogError("TCGdex devolvió una respuesta JSON inválida.") from exc
        time.sleep(0.5 * (2 ** attempt))


def text_field(data, key, length, *, required=False, url=False):
    value = data.get(key, "")
    if value is None and not required:
        value = ""
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > length:
        raise CatalogError(f"Campo inválido en TCGdex: {key}.")
    if url and value:
        try:
            URLValidator(schemes=["https", "http"])(value)
        except ValidationError as exc:
            raise CatalogError(f"URL inválida en TCGdex: {key}.") from exc
    return value


def validate_set(data):
    if not isinstance(data, dict):
        raise CatalogError("Falta el set de la carta.")
    identifier = validate_id(text_field(data, "id", 50, required=True))
    defaults = {"name": text_field(data, "name", 200, required=True)}
    # A brief set may omit logo: do not erase an already imported logo.
    if "logo" in data:
        defaults["logo"] = text_field(data, "logo", 200, url=True)
    return identifier, defaults


def import_card(card_id, *, expected_set=None):
    data = fetch_json("cards", card_id)
    identifier = validate_id(text_field(data, "id", 100, required=True))
    if identifier != card_id:
        raise CatalogError("La carta recibida no coincide con el ID solicitado.")
    set_id, set_defaults = validate_set(data.get("set"))
    if expected_set is not None and set_id != expected_set:
        raise CatalogError("La carta recibida no pertenece al set solicitado.")
    defaults = {
        "local_id": text_field(data, "localId", 20, required=True),
        "name": text_field(data, "name", 200, required=True),
        "image": text_field(data, "image", 200, url=True),
        "category": text_field(data, "category", 50),
        "rarity": text_field(data, "rarity", 100),
        "illustrator": text_field(data, "illustrator", 200),
    }
    # The HTTP request and validation run before opening a database transaction.
    with transaction.atomic():
        card_set, _ = Set.objects.update_or_create(tcgdex_id=set_id, defaults=set_defaults)
        return Card.objects.update_or_create(
            tcgdex_id=identifier, defaults={**defaults, "set": card_set}
        )


def fetch_set_cards(set_id):
    data = fetch_json("sets", set_id)
    identifier, _ = validate_set(data)
    if identifier != set_id:
        raise CatalogError("El set recibido no coincide con el ID solicitado.")
    cards = data.get("cards")
    if not isinstance(cards, list):
        raise CatalogError("El set no contiene una lista válida de cartas.")
    identifiers = []
    for card in cards:
        if not isinstance(card, dict):
            raise CatalogError("La lista del set contiene una carta inválida.")
        identifiers.append(validate_id(card.get("id")))
    return list(dict.fromkeys(identifiers))
