from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from products.models import Review, Sneaker


SEED_CUSTOMERS = [
    {
        "email": "seed.customer1@solevault.local",
        "username": "seed_customer_1",
        "first_name": "Maya",
        "last_name": "Parker",
    },
    {
        "email": "seed.customer2@solevault.local",
        "username": "seed_customer_2",
        "first_name": "Leo",
        "last_name": "Ramirez",
    },
    {
        "email": "seed.customer3@solevault.local",
        "username": "seed_customer_3",
        "first_name": "Nora",
        "last_name": "Kim",
    },
    {
        "email": "seed.customer4@solevault.local",
        "username": "seed_customer_4",
        "first_name": "Ethan",
        "last_name": "Brooks",
    },
    {
        "email": "seed.customer5@solevault.local",
        "username": "seed_customer_5",
        "first_name": "Ava",
        "last_name": "Patel",
    },
    {
        "email": "seed.customer6@solevault.local",
        "username": "seed_customer_6",
        "first_name": "Mason",
        "last_name": "Cole",
    },
]

STATUS_ORDER = ["approved", "pending", "rejected"]
COMMENTS_BY_STATUS = {
    "approved": [
        "Great comfort and solid support for all-day wear.",
        "Build quality feels premium and the fit is excellent.",
        "Really balanced sneaker with great traction.",
    ],
    "pending": [
        "Good first impression, still testing it this week.",
        "Looks amazing, deciding if sizing is perfect.",
        "Comfort is promising; will update after more use.",
    ],
    "rejected": [
        "This felt too narrow for my feet.",
        "Expected better cushioning for this price point.",
        "Material quality did not meet expectations.",
    ],
}


class Command(BaseCommand):
    help = (
        "Seed deterministic sneaker reviews (approved, pending, rejected) "
        "for local dev and moderation testing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-sneakers",
            type=int,
            default=20,
            help="How many sneakers to seed reviews for (default: 20).",
        )
        parser.add_argument(
            "--per-sneaker",
            type=int,
            default=3,
            help="How many reviews to seed per sneaker (default: 3, max: 6).",
        )
        parser.add_argument(
            "--reset-seed-reviews",
            action="store_true",
            help="Update existing seed-user reviews to match current seeded statuses/comments.",
        )

    def handle(self, *args, **options):
        max_sneakers = max(1, int(options["max_sneakers"]))
        per_sneaker = max(1, min(int(options["per_sneaker"]), len(SEED_CUSTOMERS)))
        reset_seed_reviews = bool(options["reset_seed_reviews"])

        users, created_users = self._ensure_seed_customers()
        sneakers = list(Sneaker.objects.order_by("id")[:max_sneakers])

        if not sneakers:
            self.stdout.write(self.style.WARNING("No sneakers found. Seed products first."))
            return

        created_reviews = 0
        updated_reviews = 0
        untouched_reviews = 0

        for sneaker_index, sneaker in enumerate(sneakers):
            for slot in range(per_sneaker):
                customer = users[(sneaker_index + slot) % len(users)]
                status = STATUS_ORDER[(sneaker_index + slot) % len(STATUS_ORDER)]
                comment_variants = COMMENTS_BY_STATUS[status]
                comment = comment_variants[(sneaker_index + slot) % len(comment_variants)]
                rating = 5 - ((sneaker_index + slot) % 3)

                defaults = {
                    "rating": rating,
                    "comment": comment,
                    "status": status,
                }
                review, was_created = Review.objects.get_or_create(
                    sneaker=sneaker,
                    customer=customer,
                    defaults=defaults,
                )

                if was_created:
                    created_reviews += 1
                    continue

                if not reset_seed_reviews:
                    untouched_reviews += 1
                    continue

                changed = False
                for field, value in defaults.items():
                    if getattr(review, field) != value:
                        setattr(review, field, value)
                        changed = True
                if changed:
                    review.save(update_fields=["rating", "comment", "status", "updated_at"])
                    updated_reviews += 1
                else:
                    untouched_reviews += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seed reviews complete. "
                f"customers_created={created_users}, "
                f"reviews_created={created_reviews}, "
                f"reviews_updated={updated_reviews}, "
                f"reviews_untouched={untouched_reviews}"
            )
        )

    def _ensure_seed_customers(self):
        user_model = get_user_model()
        users = []
        created_count = 0

        for customer in SEED_CUSTOMERS:
            user, was_created = user_model.objects.get_or_create(
                email=customer["email"],
                defaults={
                    "username": customer["username"],
                    "first_name": customer["first_name"],
                    "last_name": customer["last_name"],
                    "role": "customer",
                    "is_active": True,
                },
            )
            if was_created:
                user.set_password("SeedCustomer123!")
                user.save(update_fields=["password"])
                created_count += 1
            users.append(user)

        return users, created_count
