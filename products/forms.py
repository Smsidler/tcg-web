from django import forms

from .models import Order


class CartQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=9999)


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "name",
            "email",
            "phone",
            "address",
            "commune",
            "notes",
        ]
        labels = {
            "name": "Nombre completo",
            "email": "Correo electrónico",
            "phone": "Teléfono",
            "address": "Dirección",
            "commune": "Comuna",
            "notes": "Notas del pedido",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "Nombre y apellido"}
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": "correo@ejemplo.com"}
            ),
            "phone": forms.TextInput(
                attrs={"placeholder": "+56 9 1234 5678"}
            ),
            "address": forms.TextInput(
                attrs={"placeholder": "Calle, número, depto/casa"}
            ),
            "commune": forms.TextInput(
                attrs={"placeholder": "Ej: San Miguel"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "placeholder": "Información adicional para tu pedido",
                    "rows": 3,
                }
            ),
        }