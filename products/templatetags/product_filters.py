from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def clp(value):
    """Display whole pesos normally without silently truncating existing decimals."""
    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            return value
        places = 0 if amount == amount.to_integral_value() else 2
        formatted = f"{amount:,.{places}f}"
        return "$" + formatted.translate(str.maketrans({",": ".", ".": ","}))
    except (InvalidOperation, ValueError, TypeError):
        return value
