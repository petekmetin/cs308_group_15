# Generated manually for size-aware cart items

import django.db.models.deletion
from django.db import migrations, models


def purge_legacy_cart_items(apps, schema_editor):
    CartItem = apps.get_model('cart', 'CartItem')
    # Previous cart rows had no explicit size selection; remove them once.
    CartItem.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_rename_image_url_sneakerimage_image_and_more'),
        ('cart', '0002_alter_cartitem_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='sneaker',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cart_items',
                to='products.sneaker',
            ),
        ),
        migrations.AddField(
            model_name='cartitem',
            name='size',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cart_items',
                to='products.sneakersize',
            ),
        ),
        migrations.RunPython(purge_legacy_cart_items, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name='cartitem',
            name='unique_cart_product_slug',
        ),
        migrations.AlterField(
            model_name='cartitem',
            name='sneaker',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cart_items',
                to='products.sneaker',
            ),
        ),
        migrations.AlterField(
            model_name='cartitem',
            name='size',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cart_items',
                to='products.sneakersize',
            ),
        ),
        migrations.AddConstraint(
            model_name='cartitem',
            constraint=models.UniqueConstraint(
                fields=('cart', 'sneaker', 'size'),
                name='unique_cart_sneaker_size',
            ),
        ),
    ]
