"""
Run with: python manage.py shell < seed.py
Creates test users, brands, categories, sneakers, and sizes.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
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
    ('Converse', 'converse', 'Shoes Are Boring. Wear Sneakers.'),
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
    {
        'brand': 'nike', 'category': 'lifestyle',
        'name': 'Dunk Low Retro', 'model_number': 'DD1391-100',
        'colorway': 'White/Black', 'sku': 'NIKE-DUNK-WB',
        'serial_number': 'SN-NIKE-003',
        'description': 'Created for the hardwood but taken to the streets.',
        'price': '110.00', 'cost_price': '52.00',
        'warranty_status': '2 years',
        'distributor_information': 'Nike Inc.',
        'is_featured': True,
        'sizes': [
            ('7', 'US', 6), ('8', 'US', 10), ('9', 'US', 14),
            ('10', 'US', 10), ('11', 'US', 7), ('12', 'US', 3),
        ],
        'images': []
    },
    {
        'brand': 'nike', 'category': 'lifestyle',
        'name': 'Air Max 270', 'model_number': 'AH8050-002',
        'colorway': 'Black/Anthracite', 'sku': 'NIKE-AM270-BLK',
        'serial_number': 'SN-NIKE-004',
        'description': "Nike's biggest Air unit yet delivers unrivalled, all-day comfort.",
        'price': '150.00', 'cost_price': '72.00',
        'warranty_status': '2 years',
        'distributor_information': 'Nike Inc.',
        'sizes': [
            ('8', 'US', 8), ('9', 'US', 10), ('10', 'US', 9),
            ('11', 'US', 6), ('12', 'US', 4),
        ],
        'images': []
    },
    {
        'brand': 'jordan', 'category': 'basketball',
        'name': 'Air Jordan 4 Retro', 'model_number': 'FQ8138-003',
        'colorway': 'Black/Cement Grey', 'sku': 'JRD-AJ4-BLK',
        'serial_number': 'SN-JRD-002',
        'description': 'The AJ4 introduced the first plastic wing eyelets on a basketball shoe.',
        'price': '210.00', 'cost_price': '105.00',
        'warranty_status': '2 years',
        'distributor_information': 'Jordan Brand / Nike',
        'is_featured': True,
        'sizes': [
            ('8', 'US', 4), ('9', 'US', 6), ('10', 'US', 8),
            ('11', 'US', 5), ('12', 'US', 3),
        ],
        'images': []
    },
    {
        'brand': 'jordan', 'category': 'basketball',
        'name': 'Air Jordan 11 Retro', 'model_number': '378037-006',
        'colorway': 'Black/Dark Concord-White', 'sku': 'JRD-AJ11-CON',
        'serial_number': 'SN-JRD-003',
        'description': 'Patent leather upper and translucent outsole — the most iconic Jordan ever made.',
        'price': '220.00', 'cost_price': '110.00',
        'warranty_status': '2 years',
        'distributor_information': 'Jordan Brand / Nike — limited release',
        'discount_percentage': 5,
        'sizes': [
            ('8', 'US', 3), ('9', 'US', 5), ('10', 'US', 6),
            ('11', 'US', 4), ('12', 'US', 2),
        ],
        'images': []
    },
    {
        'brand': 'jordan', 'category': 'lifestyle',
        'name': 'Air Jordan 3 Retro', 'model_number': 'CT8532-016',
        'colorway': 'Black/Cement Grey-White-Fire Red', 'sku': 'JRD-AJ3-BLK',
        'serial_number': 'SN-JRD-004',
        'description': 'The first Jordan designed by Tinker Hatfield, featuring the iconic elephant print.',
        'price': '200.00', 'cost_price': '98.00',
        'warranty_status': '2 years',
        'distributor_information': 'Jordan Brand / Nike',
        'sizes': [
            ('8', 'US', 5), ('9', 'US', 7), ('10', 'US', 9),
            ('11', 'US', 6), ('12', 'US', 3),
        ],
        'images': []
    },
    {
        'brand': 'adidas', 'category': 'running',
        'name': 'Ultraboost 22', 'model_number': 'GZ0127',
        'colorway': 'Core Black/Carbon', 'sku': 'ADI-UB22-BLK',
        'serial_number': 'SN-ADI-002',
        'description': 'Our most responsive running shoe, made in part with Parley Ocean Plastic.',
        'price': '190.00', 'cost_price': '92.00',
        'warranty_status': '1 year',
        'distributor_information': 'Adidas AG',
        'is_featured': True,
        'sizes': [
            ('7', 'US', 6), ('8', 'US', 10), ('9', 'US', 12),
            ('10', 'US', 9), ('11', 'US', 5),
        ],
        'images': []
    },
    {
        'brand': 'adidas', 'category': 'lifestyle',
        'name': 'Superstar', 'model_number': 'EG4958',
        'colorway': 'Cloud White/Core Black', 'sku': 'ADI-SS-WHT',
        'serial_number': 'SN-ADI-003',
        'description': 'The shell toe original. A street icon since 1969.',
        'price': '99.99', 'cost_price': '48.00',
        'warranty_status': '1 year',
        'distributor_information': 'Adidas AG',
        'sizes': [
            ('7', 'US', 9), ('8', 'US', 13), ('9', 'US', 11),
            ('10', 'US', 8), ('11', 'US', 5), ('12', 'US', 3),
        ],
        'images': []
    },
    {
        'brand': 'adidas', 'category': 'lifestyle',
        'name': 'Forum Low', 'model_number': 'FY7757',
        'colorway': 'Cloud White/Cloud White', 'sku': 'ADI-FORUM-WHT',
        'serial_number': 'SN-ADI-004',
        'description': 'Basketball heritage meets street style. The Forum is back.',
        'price': '99.99', 'cost_price': '47.00',
        'warranty_status': '1 year',
        'distributor_information': 'Adidas AG',
        'sizes': [
            ('7', 'US', 7), ('8', 'US', 11), ('9', 'US', 10),
            ('10', 'US', 8), ('11', 'US', 4),
        ],
        'images': []
    },
    {
        'brand': 'puma', 'category': 'lifestyle',
        'name': 'Suede Classic XXI', 'model_number': '374915-01',
        'colorway': 'Puma Black/Puma Team Gold', 'sku': 'PUMA-SUEDE-BLK',
        'serial_number': 'SN-PUMA-001',
        'description': 'The Suede has been changing the game since 1968. A true icon.',
        'price': '75.00', 'cost_price': '35.00',
        'warranty_status': '1 year',
        'distributor_information': 'Puma SE',
        'is_featured': True,
        'sizes': [
            ('7', 'US', 10), ('8', 'US', 14), ('9', 'US', 12),
            ('10', 'US', 9), ('11', 'US', 6), ('12', 'US', 3),
        ],
        'images': []
    },
    {
        'brand': 'puma', 'category': 'lifestyle',
        'name': 'RS-X³ Puzzle', 'model_number': '371570-01',
        'colorway': 'Puma White/Puma Black', 'sku': 'PUMA-RSX-WHT',
        'serial_number': 'SN-PUMA-002',
        'description': 'Chunky, bold, and futuristic. The RS-X brings back the 80s running aesthetic.',
        'price': '110.00', 'cost_price': '52.00',
        'warranty_status': '1 year',
        'distributor_information': 'Puma SE',
        'sizes': [
            ('7', 'US', 8), ('8', 'US', 11), ('9', 'US', 10),
            ('10', 'US', 7), ('11', 'US', 4),
        ],
        'images': []
    },
    {
        'brand': 'puma', 'category': 'lifestyle',
        'name': 'Clyde All-Pro', 'model_number': '194039-01',
        'colorway': 'Puma Navy/Puma Gold', 'sku': 'PUMA-CLYDE-NVY',
        'serial_number': 'SN-PUMA-003',
        'description': 'Named after Walt "Clyde" Frazier. Performance meets style on the hardwood.',
        'price': '95.00', 'cost_price': '44.00',
        'warranty_status': '1 year',
        'distributor_information': 'Puma SE',
        'sizes': [
            ('8', 'US', 7), ('9', 'US', 9), ('10', 'US', 10),
            ('11', 'US', 6), ('12', 'US', 3),
        ],
        'images': []
    },
    {
        'brand': 'converse', 'category': 'lifestyle',
        'name': 'Chuck Taylor All Star', 'model_number': 'M9160',
        'colorway': 'Black/Black', 'sku': 'CONV-CTAS-BLK',
        'serial_number': 'SN-CONV-001',
        'description': 'The original basketball shoe turned cultural icon. Worn by everyone, everywhere.',
        'price': '60.00', 'cost_price': '28.00',
        'warranty_status': '1 year',
        'distributor_information': 'Converse Inc. / Nike',
        'is_featured': True,
        'sizes': [
            ('6', 'US', 10), ('7', 'US', 14), ('8', 'US', 16),
            ('9', 'US', 13), ('10', 'US', 9), ('11', 'US', 6), ('12', 'US', 3),
        ],
        'images': []
    },
    {
        'brand': 'converse', 'category': 'lifestyle',
        'name': 'Chuck Taylor All Star Hi', 'model_number': 'M9160C',
        'colorway': 'Optical White', 'sku': 'CONV-CTASHI-WHT',
        'serial_number': 'SN-CONV-002',
        'description': 'The high-top silhouette that started it all. A timeless classic in clean white.',
        'price': '65.00', 'cost_price': '30.00',
        'warranty_status': '1 year',
        'distributor_information': 'Converse Inc. / Nike',
        'sizes': [
            ('6', 'US', 8), ('7', 'US', 12), ('8', 'US', 15),
            ('9', 'US', 11), ('10', 'US', 8), ('11', 'US', 5),
        ],
        'images': []
    },
    {
        'brand': 'converse', 'category': 'skate',
        'name': 'One Star Pro', 'model_number': '162542C',
        'colorway': 'Black/Black-White', 'sku': 'CONV-ONESTAR-BLK',
        'serial_number': 'SN-CONV-003',
        'description': 'Low-profile skate shoe with suede upper and OrthoLite cushioning.',
        'price': '70.00', 'cost_price': '33.00',
        'warranty_status': '1 year',
        'distributor_information': 'Converse Inc. / Nike',
        'sizes': [
            ('7', 'US', 9), ('8', 'US', 12), ('9', 'US', 11),
            ('10', 'US', 8), ('11', 'US', 5), ('12', 'US', 2),
        ],
        'images': []
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

    # Note: intentionally not seeding SneakerImage rows. The frontend has a
    # tasteful fallback for products without images and we don't want to ship
    # hot-linked photos that might not match the actual product.
    _ = images_data  # retained in sneakers_data for future use
    _ = SneakerImage  # keep import referenced for migrations/admin scripts

    print(f'  Created sneaker: {sneaker.brand.name} {sneaker.name}')

print("\n✓ Seed complete.")
print(f"\nTest credentials:")
print(f"  Customer:         customer@test.com   / TestPass123!")
print(f"  Sales Manager:    sales@test.com      / TestPass123!")
print(f"  Product Manager:  product@test.com    / TestPass123!")