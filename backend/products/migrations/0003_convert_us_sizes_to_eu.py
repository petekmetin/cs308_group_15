from decimal import Decimal, InvalidOperation

from django.db import migrations


US_TO_EU_MAP = {
    Decimal('6'): '39',
    Decimal('6.5'): '39.5',
    Decimal('7'): '40',
    Decimal('7.5'): '40.5',
    Decimal('8'): '41',
    Decimal('8.5'): '41.5',
    Decimal('9'): '42',
    Decimal('9.5'): '42.5',
    Decimal('10'): '43',
    Decimal('10.5'): '43.5',
    Decimal('11'): '44',
    Decimal('11.5'): '44.5',
    Decimal('12'): '45',
    Decimal('12.5'): '45.5',
    Decimal('13'): '46',
    Decimal('13.5'): '46.5',
    Decimal('14'): '47',
}


def _decimal_to_label(value):
    text = format(value, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text


def convert_us_size_value_to_eu_label(raw_size):
    raw_text = str(raw_size).strip()
    try:
        parsed = Decimal(raw_text)
    except (InvalidOperation, TypeError):
        return raw_text

    if parsed in US_TO_EU_MAP:
        return US_TO_EU_MAP[parsed]

    # Fallback for numeric sizes not in the mapping table.
    return _decimal_to_label(parsed + Decimal('33'))


def convert_us_rows_to_eu(apps, schema_editor):
    SneakerSize = apps.get_model('products', 'SneakerSize')

    for row in SneakerSize.objects.filter(size_system='US').order_by('id').iterator():
        eu_size_value = convert_us_size_value_to_eu_label(row.size)

        existing_eu_row = SneakerSize.objects.filter(
            sneaker_id=row.sneaker_id,
            size_system='EU',
            size=eu_size_value,
        ).exclude(id=row.id).first()

        if existing_eu_row:
            existing_eu_row.stock = (existing_eu_row.stock or 0) + (row.stock or 0)
            existing_eu_row.save(update_fields=['stock'])
            row.delete()
            continue

        row.size_system = 'EU'
        row.size = eu_size_value
        row.save(update_fields=['size_system', 'size'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_rename_image_url_sneakerimage_image_and_more'),
    ]

    operations = [
        migrations.RunPython(convert_us_rows_to_eu, migrations.RunPython.noop),
    ]
