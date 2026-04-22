from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import BaseCommand, CommandError, call_command

from products.models import Brand, Category, Sneaker, SneakerImage, SneakerSize

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


FALLBACK_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XlqQAAAAASUVORK5CYII="
)

US_TO_EU_MAP = {
    Decimal("6"): "39",
    Decimal("6.5"): "39.5",
    Decimal("7"): "40",
    Decimal("7.5"): "40.5",
    Decimal("8"): "41",
    Decimal("8.5"): "41.5",
    Decimal("9"): "42",
    Decimal("9.5"): "42.5",
    Decimal("10"): "43",
    Decimal("10.5"): "43.5",
    Decimal("11"): "44",
    Decimal("11.5"): "44.5",
    Decimal("12"): "45",
    Decimal("12.5"): "45.5",
    Decimal("13"): "46",
    Decimal("13.5"): "46.5",
    Decimal("14"): "47",
}


class Command(BaseCommand):
    help = (
        "Load shared products fixture and generate missing image files so catalog is consistent "
        "across developer environments."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="products/fixtures/products_seed.json",
            help="Fixture path relative to backend manage.py location.",
        )
        parser.add_argument(
            "--skip-reviews",
            action="store_true",
            help="Skip seeding deterministic review data.",
        )
        parser.add_argument(
            "--with-migrate",
            action="store_true",
            help="Run migrate before loading fixture (single-command setup for fresh environments).",
        )

    def handle(self, *args, **options):
        fixture_path = Path(options["fixture"])

        if options.get("with_migrate"):
            self.stdout.write("Running migrations before bootstrap (--with-migrate)...")
            call_command("migrate", interactive=False)

        self.stdout.write(f"Loading fixture: {fixture_path}")
        call_command("loaddata", str(fixture_path))

        converted_sizes, merged_sizes = self._normalize_sizes_to_eu()

        created_files = 0
        existing_files = 0

        for image in SneakerImage.objects.select_related("sneaker"):
            image_name = str(image.image.name or "").strip()
            if not image_name:
                continue

            if default_storage.exists(image_name):
                existing_files += 1
                continue

            payload = self._build_image_bytes(seed=image.sneaker_id or image.id)
            saved_name = default_storage.save(image_name, ContentFile(payload))
            image.image.name = saved_name
            image.save(update_fields=["image"])
            created_files += 1

        self._validate_catalog_integrity()

        self.stdout.write(
            self.style.SUCCESS(
                "Bootstrap complete. "
                f"EU size normalization: converted={converted_sizes}, merged={merged_sizes}. "
                f"Existing image files: {existing_files}, created missing files: {created_files}."
            )
        )

        if options.get("skip_reviews"):
            self.stdout.write("Skipping seed_sneaker_reviews (--skip-reviews).")
        else:
            self.stdout.write("Seeding review data for moderation/testing...")
            call_command("seed_sneaker_reviews")

    def _normalize_sizes_to_eu(self):
        converted_rows = 0
        merged_rows = 0

        for row in SneakerSize.objects.filter(size_system="US").order_by("id").iterator():
            eu_size_value = self._convert_us_size_value_to_eu_label(row.size)
            existing_eu_row = (
                SneakerSize.objects.filter(
                    sneaker_id=row.sneaker_id,
                    size_system="EU",
                    size=eu_size_value,
                )
                .exclude(id=row.id)
                .first()
            )

            if existing_eu_row:
                existing_eu_row.stock = (existing_eu_row.stock or 0) + (row.stock or 0)
                existing_eu_row.save(update_fields=["stock"])
                row.delete()
                merged_rows += 1
                continue

            row.size_system = "EU"
            row.size = eu_size_value
            row.save(update_fields=["size_system", "size"])
            converted_rows += 1

        return converted_rows, merged_rows

    def _convert_us_size_value_to_eu_label(self, raw_size):
        raw_text = str(raw_size).strip()
        try:
            parsed = Decimal(raw_text)
        except (InvalidOperation, TypeError):
            return raw_text

        if parsed in US_TO_EU_MAP:
            return US_TO_EU_MAP[parsed]

        # Fallback for uncommon numeric sizes not explicitly mapped above.
        return self._decimal_to_label(parsed + Decimal("33"))

    def _decimal_to_label(self, value):
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _validate_catalog_integrity(self):
        missing_brand = Sneaker.objects.filter(brand__isnull=True).count()
        missing_category = Sneaker.objects.filter(category__isnull=True).count()
        missing_images = Sneaker.objects.filter(images__isnull=True).count()
        blank_image_paths = SneakerImage.objects.filter(image="").count()

        if any([missing_brand, missing_category, missing_images, blank_image_paths]):
            raise CommandError(
                "Catalog bootstrap integrity check failed: "
                f"missing_brand={missing_brand}, "
                f"missing_category={missing_category}, "
                f"missing_images={missing_images}, "
                f"blank_image_paths={blank_image_paths}."
            )

        self.stdout.write(
            "Catalog integrity OK: "
            f"brands={Brand.objects.count()}, "
            f"categories={Category.objects.count()}, "
            f"sneakers={Sneaker.objects.count()}, "
            f"sizes={SneakerSize.objects.count()}, "
            f"images={SneakerImage.objects.count()}."
        )

    def _build_image_bytes(self, seed: int) -> bytes:
        if Image is None:
            return FALLBACK_PNG_BYTES

        width, height = 1200, 900
        color = (
            (40 + seed * 7) % 255,
            (100 + seed * 11) % 255,
            (160 + seed * 5) % 255,
        )
        generated = Image.new("RGB", (width, height), color=color)

        buffer = BytesIO()
        generated.save(buffer, format="WEBP", quality=82, method=6)
        return buffer.getvalue()
