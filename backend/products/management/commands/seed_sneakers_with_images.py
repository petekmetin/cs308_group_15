from __future__ import annotations

import base64
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from products.models import Brand, Category, Sneaker, SneakerImage, SneakerSize

try:
    from PIL import Image
except ImportError:  # pragma: no cover - fallback for environments without Pillow
    Image = None


# 1x1 transparent PNG fallback
FALLBACK_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XlqQAAAAASUVORK5CYII="
)


SNEAKER_SEED_DATA = [
    {"name": "Air Zoom Tempo", "brand": "Nike", "category": "Running", "colorway": "Black/Volt"},
    {"name": "Ultraboost Light", "brand": "Adidas", "category": "Running", "colorway": "White/Core Black"},
    {"name": "Gel-Kayano 30", "brand": "ASICS", "category": "Running", "colorway": "Blue/Orange"},
    {"name": "574 Legacy", "brand": "New Balance", "category": "Lifestyle", "colorway": "Grey/Navy"},
    {"name": "RS-X Heritage", "brand": "Puma", "category": "Lifestyle", "colorway": "White/Red"},
    {"name": "Air Jordan 4 Retro", "brand": "Jordan", "category": "Basketball", "colorway": "Bred"},
    {"name": "Dame 9", "brand": "Adidas", "category": "Basketball", "colorway": "Core Black/Gold"},
    {"name": "KD 17", "brand": "Nike", "category": "Basketball", "colorway": "Purple/Teal"},
    {"name": "One Star Pro", "brand": "Converse", "category": "Skate", "colorway": "Black/White"},
    {"name": "SB Dunk Low Pro", "brand": "Nike", "category": "Skate", "colorway": "Green/Gum"},
    {"name": "Nano X4", "brand": "Reebok", "category": "Training", "colorway": "Grey/Blue"},
    {"name": "Metcon 10", "brand": "Nike", "category": "Training", "colorway": "Black/Red"},
    {"name": "Wave Rider 28", "brand": "Mizuno", "category": "Running", "colorway": "Navy/Silver"},
    {"name": "Forum Low CL", "brand": "Adidas", "category": "Lifestyle", "colorway": "White/Green"},
    {"name": "Chuck 70 High", "brand": "Converse", "category": "Lifestyle", "colorway": "Parchment"},
    {"name": "Suede Classic XXI", "brand": "Puma", "category": "Lifestyle", "colorway": "Navy/White"},
    {"name": "GT Hustle 3", "brand": "Nike", "category": "Basketball", "colorway": "White/Crimson"},
    {"name": "Fresh Foam 1080", "brand": "New Balance", "category": "Running", "colorway": "Sea Salt/Blue"},
    {"name": "Sk8-Hi", "brand": "Vans", "category": "Skate", "colorway": "Black/True White"},
    {"name": "Clyde All-Pro", "brand": "Puma", "category": "Basketball", "colorway": "Orange/Black"},
]


class Command(BaseCommand):
    help = "Seed 20 sneaker records with local image files, sizes, and pricing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=20,
            help="How many entries to seed (max 20 with current dataset).",
        )

    def handle(self, *args, **options):
        count = max(1, min(options["count"], len(SNEAKER_SEED_DATA)))
        created = 0
        skipped = 0

        for index, entry in enumerate(SNEAKER_SEED_DATA[:count], start=1):
            brand = self._get_brand(entry["brand"])
            category = self._get_category(entry["category"])
            sku = f"{slugify(brand.name)[:8].upper()}-AUTO-{index:03d}"
            serial = f"SER-AUTO-{index:04d}"

            sneaker, was_created = Sneaker.objects.get_or_create(
                sku=sku,
                defaults={
                    "brand": brand,
                    "category": category,
                    "name": entry["name"],
                    "model_number": f"MDL-{index:04d}",
                    "colorway": entry["colorway"],
                    "description": (
                        f"{entry['name']} by {brand.name}. Seeded product for local dev and test data."
                    ),
                    "serial_number": serial,
                    "price": Decimal("99.99") + Decimal(index * 5),
                    "original_price": Decimal("109.99") + Decimal(index * 5),
                    "cost_price": Decimal("55.00") + Decimal(index),
                    "discount_percentage": Decimal("0.00"),
                    "warranty_status": "1 year",
                    "distributor_information": "Local seed data distributor",
                    "is_active": True,
                    "is_featured": index % 5 == 0,
                    "popularity_score": 100 - index,
                },
            )

            if not was_created:
                skipped += 1
                self.stdout.write(f"Skipping existing sneaker {sku}")
                continue

            created += 1
            self._create_sizes(sneaker)
            self._create_images(sneaker, index)
            self.stdout.write(self.style.SUCCESS(f"Created {sneaker.name} ({sku})"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Seed complete. Created={created}, Skipped={skipped}"))

    def _get_brand(self, name: str) -> Brand:
        slug = slugify(name)
        brand, _ = Brand.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": f"{name} seeded brand",
            },
        )
        return brand

    def _get_category(self, name: str) -> Category:
        slug = slugify(name)
        category, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": f"{name} seeded category",
            },
        )
        return category

    def _create_sizes(self, sneaker: Sneaker) -> None:
        sizes = [("8", 4), ("9", 7), ("10", 9), ("11", 6), ("12", 3)]
        for size, stock in sizes:
            SneakerSize.objects.create(
                sneaker=sneaker,
                size=size,
                size_system="US",
                stock=stock,
            )

    def _create_images(self, sneaker: Sneaker, seed_number: int) -> None:
        primary_bytes = self._build_image_bytes(seed_number, variant=0)
        secondary_bytes = self._build_image_bytes(seed_number, variant=1)

        primary_name = f"{slugify(sneaker.sku)}-primary.webp"
        secondary_name = f"{slugify(sneaker.sku)}-side.webp"

        SneakerImage.objects.create(
            sneaker=sneaker,
            image=ContentFile(primary_bytes, name=primary_name),
            alt_text=f"{sneaker.name} primary",
            is_primary=True,
            order=0,
        )
        SneakerImage.objects.create(
            sneaker=sneaker,
            image=ContentFile(secondary_bytes, name=secondary_name),
            alt_text=f"{sneaker.name} side view",
            is_primary=False,
            order=1,
        )

    def _build_image_bytes(self, seed_number: int, variant: int) -> bytes:
        if Image is None:
            return FALLBACK_PNG_BYTES

        width, height = 1200, 900
        base = (
            (40 + seed_number * 7 + variant * 20) % 255,
            (80 + seed_number * 9 + variant * 35) % 255,
            (120 + seed_number * 11 + variant * 15) % 255,
        )
        image = Image.new("RGB", (width, height), color=base)

        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=85, method=6)
        return buffer.getvalue()
