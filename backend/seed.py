"""
Run with: python manage.py shell < seed.py
Creates test users, brands, categories, sneakers, and sizes.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User
from products.models import Brand, Category, Sneaker, SneakerSize, SneakerImage

print("Seeding users...")

def create_user(email, username, first, last, role, password='TestPass123!', **kwargs):
    if User.objects.filter(email=email).exists():
        print(f'  Skipping {email} (already exists)')
        return User.objects.get(email=email)
    u = User(email=email, username=username, first_name=first, last_name=last, role=role, **kwargs)
    u.set_password(password)
    u.save()
    print(f'  Created {role}: {email}')
    return u

customer1 = create_user(
    'customer@test.com', 'johndoe', 'John', 'Doe', 'customer',
    tax_id='TC-001', home_address='123 Main St, Istanbul'
)
customer2 = create_user(
    'jane@test.com', 'janedoe', 'Jane', 'Doe', 'customer',
    tax_id='TC-002', home_address='456 Oak Ave, Ankara'
)
sales_mgr = create_user(
    'sales@test.com', 'salesmgr', 'Sarah', 'Smith', 'sales_manager'
)
prod_mgr = create_user(
    'product@test.com', 'prodmgr', 'Peter', 'Park', 'product_manager'
)

print("\nSeeding brands...")

brands_data = [
    ('Nike', 'nike', 'Just Do It.'),
    ('Adidas', 'adidas', 'Impossible Is Nothing.'),
    ('Jordan', 'jordan', 'Air Jordan brand by Nike.'),
    ('New Balance', 'new-balance', 'Fearlessly Independent.'),
    ('Puma', 'puma', 'Forever Faster.'),
]

brands = {}
for name, slug, desc in brands_data:
    b, created = Brand.objects.get_or_create(slug=slug, defaults={'name': name, 'description': desc})
    brands[slug] = b
    print(f'  {"Created" if created else "Exists"}: {name}')

print("\nSeeding categories...")

categories_data = [
    ('Lifestyle', 'lifestyle', 'Everyday casual sneakers'),
    ('Basketball', 'basketball', 'High-performance basketball shoes'),
    ('Running', 'running', 'Engineered for speed and comfort'),
    ('Skate', 'skate', 'Built for the board'),
    ('Training', 'training', 'Gym and cross-training footwear'),
]

categories = {}
for name, slug, desc in categories_data:
    c, created = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'description': desc})
    categories[slug] = c
    print(f'  {"Created" if created else "Exists"}: {name}')

print("\nSeeding sneakers...")

sneakers_data = [
    {
        'brand': 'nike', 'category': 'lifestyle',
        'name': "Air Force 1 '07", 'model_number': 'CW2288-111',
        'colorway': 'White/White-White', 'sku': 'NIKE-AF1-WHITE',
        'serial_number': 'SN-NIKE-001',
        'description': 'The radically simple AF1 defined a sneaker era.',
        'price': '109.99', 'cost_price': '55.00',
        'warranty_status': '2 years manufacturer warranty',
        'distributor_information': 'Nike Inc. — distributed via Nike Direct',
        'is_featured': True,
        'sizes': [
            ('7', 'US', 5), ('8', 'US', 10), ('9', 'US', 15),
            ('10', 'US', 12), ('11', 'US', 8), ('12', 'US', 4),
        ],
        'images': [
            ('https://static.nike.com/af1-white-1.jpg', True),
            ('https://static.nike.com/af1-white-2.jpg', False),
        ]
    },
    {
        'brand': 'adidas', 'category': 'lifestyle',
        'name': 'Stan Smith', 'model_number': 'M20324',
        'colorway': 'Cloud White/Green', 'sku': 'ADI-STAN-GRN',
        'serial_number': 'SN-ADI-001',
        'description': 'A tennis classic reborn. Clean, minimal, timeless.',
        'price': '89.99', 'cost_price': '42.00',
        'warranty_status': '1 year',
        'distributor_information': 'Adidas AG — distributed globally',
        'is_featured': True,
        'sizes': [
            ('7', 'US', 8), ('8', 'US', 12), ('9', 'US', 10),
            ('10', 'US', 9), ('11', 'US', 5),
        ],
        'images': [
            ('https://assets.adidas.com/stan-smith-1.jpg', True),
        ]
    },
    {
        'brand': 'jordan', 'category': 'basketball',
        'name': 'Air Jordan 1 Retro High OG', 'model_number': '555088-161',
        'colorway': 'White/Varsity Red-Black', 'sku': 'JRD-AJ1-RED',
        'serial_number': 'SN-JRD-001',
        'description': 'The shoe that started it all. Chicago colourway.',
        'price': '180.00', 'cost_price': '90.00',
        'warranty_status': '2 years',
        'distributor_information': 'Jordan Brand / Nike — limited release',
        'is_featured': True,
        'discount_percentage': 10,
        'sizes': [
            ('8', 'US', 3), ('9', 'US', 5), ('10', 'US', 7),
            ('11', 'US', 4), ('12', 'US', 2),
        ],
        'images': [
            ('https://static.nike.com/aj1-chicago-1.jpg', True),
            ('https://static.nike.com/aj1-chicago-2.jpg', False),
        ]
    },
    {
        'brand': 'new-balance', 'category': 'running',
        'name': '990v6', 'model_number': 'M990GL6',
        'colorway': 'Grey/Silver', 'sku': 'NB-990V6-GRY',
        'serial_number': 'SN-NB-001',
        'description': 'Made in USA. Premium cushioning, heritage silhouette.',
        'price': '199.99', 'cost_price': '100.00',
        'warranty_status': '1 year',
        'distributor_information': 'New Balance Athletics — made in USA line',
        'sizes': [
            ('8', 'US', 6), ('9', 'US', 8), ('10', 'US', 10),
            ('11', 'US', 7), ('12', 'US', 4),
        ],
        'images': [
            ('https://nb.com/990v6-grey-1.jpg', True),
        ]
    },
    {
        'brand': 'nike', 'category': 'running',
        'name': 'Air Max 90', 'model_number': 'CN8490-001',
        'colorway': 'Black/White-Dark Grey', 'sku': 'NIKE-AM90-BLK',
        'serial_number': 'SN-NIKE-002',
        'description': 'Visible Air cushioning. A running icon since 1990.',
        'price': '130.00', 'cost_price': '62.00',
        'warranty_status': '2 years',
        'distributor_information': 'Nike Inc.',
        'sizes': [
            ('7', 'US', 4), ('8', 'US', 9), ('9', 'US', 11),
            ('10', 'US', 8), ('11', 'US', 6),
        ],
        'images': [
            ('https://static.nike.com/am90-black-1.jpg', True),
        ]
    },
]

for data in sneakers_data:
    sku = data['sku']
    if Sneaker.objects.filter(sku=sku).exists():
        print(f'  Skipping {sku} (already exists)')
        continue

    sizes_data = data.pop('sizes')
    images_data = data.pop('images')
    brand_slug = data.pop('brand')
    cat_slug = data.pop('category')

    sneaker = Sneaker.objects.create(
        brand=brands[brand_slug],
        category=categories[cat_slug],
        **data
    )

    for size_val, system, stock in sizes_data:
        SneakerSize.objects.create(sneaker=sneaker, size=size_val, size_system=system, stock=stock)

    for url, is_primary in images_data:
        SneakerImage.objects.create(sneaker=sneaker, image_url=url, is_primary=is_primary)

    print(f'  Created sneaker: {sneaker.brand.name} {sneaker.name}')

print("\n✓ Seed complete.")
print(f"\nTest credentials:")
print(f"  Customer:         customer@test.com   / TestPass123!")
print(f"  Sales Manager:    sales@test.com      / TestPass123!")
print(f"  Product Manager:  product@test.com    / TestPass123!")