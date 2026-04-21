from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import BaseCommand, call_command

from products.models import SneakerImage

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


FALLBACK_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XlqQAAAAASUVORK5CYII="
)


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

    def handle(self, *args, **options):
        fixture_path = Path(options["fixture"])
        self.stdout.write(f"Loading fixture: {fixture_path}")
        call_command("loaddata", str(fixture_path))

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

        self.stdout.write(
            self.style.SUCCESS(
                f"Bootstrap complete. Existing image files: {existing_files}, created missing files: {created_files}"
            )
        )

        if options.get("skip_reviews"):
            self.stdout.write("Skipping seed_sneaker_reviews (--skip-reviews).")
        else:
            self.stdout.write("Seeding review data for moderation/testing...")
            call_command("seed_sneaker_reviews")

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
