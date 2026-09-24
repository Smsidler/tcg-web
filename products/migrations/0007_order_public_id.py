import uuid

from django.db import migrations, models


def generate_unique_public_ids(apps, schema_editor):
    Order = apps.get_model("products", "Order")

    for order in Order.objects.all():
        order.public_id = uuid.uuid4()
        order.save(update_fields=["public_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0006_order_stock_restored"),
    ]

    operations = [
        # 1. Agregamos temporalmente el campo sin unique=True
        migrations.AddField(
            model_name="order",
            name="public_id",
            field=models.UUIDField(
                null=True,
                editable=False,
            ),
        ),

        # 2. Generamos un UUID diferente para cada pedido existente
        migrations.RunPython(
            generate_unique_public_ids,
            migrations.RunPython.noop,
        ),

        # 3. Una vez que todos tienen UUID, activamos unique=True
        migrations.AlterField(
            model_name="order",
            name="public_id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]