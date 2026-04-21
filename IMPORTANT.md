# IMPORTANT: Inventory Bootstrap Required Before Using the App

Every developer must initialize the shared inventory data before testing `/home`, cart flows, or product APIs.

## Why this is required
- Product, brand, category, size, and sneaker-image metadata are shared via a fixture.
- Without loading this fixture, local DBs will have inconsistent catalog data and search/filter behavior.
- `backend/media/` is now transferable in the repository, so image files can be shared across developers.

## Run this before usage (mandatory)
From project root:

```bash
cd backend
./venv/bin/python manage.py migrate
./venv/bin/python manage.py bootstrap_products_catalog
```

## What `bootstrap_products_catalog` does
1. Loads shared fixture data from `backend/products/fixtures/products_seed.json`.
2. Ensures sneaker image file references are valid in your local media storage (creates missing files only if needed).

## When to run again
- After pulling new changes that include product fixture updates.
- After resetting/recreating your local database.
- If product list/search results look empty or inconsistent with teammates.

## If someone updates inventory data
They must regenerate and commit the fixture:

```bash
cd backend
./venv/bin/python manage.py dumpdata products.Brand products.Category products.Sneaker products.SneakerSize products.SneakerImage --indent 2 --output products/fixtures/products_seed.json
```

Then teammates pull and rerun bootstrap.
