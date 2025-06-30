#!/usr/bin/env python3
import os
import sys
import django

# เพิ่ม path ของ project
sys.path.append('/home/nithiwit/Documents/project')

# ตั้งค่า Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Storems.settings')
django.setup()

from App_Products.models import Product, Category, Brand
from decimal import Decimal

def create_sample_data():
    print('=== สร้างข้อมูลตัวอย่าง ===')
    
    # ลบข้อมูลเก่าก่อน
    print('ลบข้อมูลเก่า...')
    Product.objects.all().delete()
    Category.objects.all().delete()
    Brand.objects.all().delete()
    
    # สร้าง Category
    category1 = Category.objects.create(
        name='อิเล็กทรอนิกส์',
        category_code='001', 
        description='สินค้าอิเล็กทรอนิกส์'
    )
    print(f'สร้าง Category: {category1.name}')
    
    category2 = Category.objects.create(
        name='เสื้อผ้า',
        category_code='002', 
        description='เสื้อผ้าและแฟชั่น'
    )
    print(f'สร้าง Category: {category2.name}')

    # สร้าง Brand
    brand1 = Brand.objects.create(
        name='Samsung',
        brand_code='1001', 
        description='แบรนด์ Samsung'
    )
    print(f'สร้าง Brand: {brand1.name}')
    
    brand2 = Brand.objects.create(
        name='Apple',
        brand_code='1002', 
        description='แบรนด์ Apple'
    )
    print(f'สร้าง Brand: {brand2.name}')

    # สร้างสินค้าตัวอย่าง
    products_data = [
        {
            'name': 'Samsung Galaxy S24',
            'cost_price': Decimal('20000'),
            'price_a': Decimal('25000'),
            'price_aa': Decimal('24000'),
            'price_aaa': Decimal('23000'),
            'category': category1,
            'brand': brand1,
            'unit': 'ชิ้น',
            'description': 'สมาร์ทโฟน Samsung รุ่นล่าสุด'
        },
        {
            'name': 'iPhone 15 Pro',
            'cost_price': Decimal('35000'),
            'price_a': Decimal('45000'),
            'price_aa': Decimal('43000'),
            'price_aaa': Decimal('41000'),
            'category': category1,
            'brand': brand2,
            'unit': 'ชิ้น',
            'description': 'iPhone รุ่นใหม่ล่าสุด'
        },
        {
            'name': 'เสื้อโปโล Samsung',
            'cost_price': Decimal('200'),
            'price_a': Decimal('350'),
            'price_aa': Decimal('320'),
            'price_aaa': Decimal('300'),
            'category': category2,
            'brand': brand1,
            'unit': 'ตัว',
            'description': 'เสื้อโปโลแบรนด์ Samsung'
        },
        {
            'name': 'เสื้อยืด Apple',
            'cost_price': Decimal('150'),
            'price_a': Decimal('250'),
            'price_aa': Decimal('230'),
            'price_aaa': Decimal('220'),
            'category': category2,
            'brand': brand2,
            'unit': 'ตัว',
            'description': 'เสื้อยืดแบรนด์ Apple'
        },
        {
            'name': 'หูฟัง Samsung Buds',
            'cost_price': Decimal('1500'),
            'price_a': Decimal('2500'),
            'price_aa': Decimal('2300'),
            'price_aaa': Decimal('2100'),
            'category': category1,
            'brand': brand1,
            'unit': 'คู่',
            'description': 'หูฟังไร้สาย Samsung'
        }
    ]

    print('\n=== สร้างสินค้าตัวอย่าง ===')
    products_data = [
        {
            'name': 'Samsung Galaxy S24',
            'cost_price': Decimal('20000'),
            'price_a': Decimal('25000'),
            'price_aa': Decimal('24000'),
            'price_aaa': Decimal('23000'),
            'category': category1,
            'brand': brand1,
            'unit': 'ชิ้น',
            'description': 'สมาร์ทโฟน Samsung รุ่นล่าสุด'
        },
        {
            'name': 'iPhone 15 Pro',
            'cost_price': Decimal('35000'),
            'price_a': Decimal('45000'),
            'price_aa': Decimal('43000'),
            'price_aaa': Decimal('41000'),
            'category': category1,
            'brand': brand2,
            'unit': 'ชิ้น',
            'description': 'iPhone รุ่นใหม่ล่าสุด'
        },
        {
            'name': 'เสื้อโปโล Samsung',
            'cost_price': Decimal('200'),
            'price_a': Decimal('350'),
            'price_aa': Decimal('320'),
            'price_aaa': Decimal('300'),
            'category': category2,
            'brand': brand1,
            'unit': 'ตัว',
            'description': 'เสื้อโปโลแบรนด์ Samsung'
        },
        {
            'name': 'เสื้อยืด Apple',
            'cost_price': Decimal('150'),
            'price_a': Decimal('250'),
            'price_aa': Decimal('230'),
            'price_aaa': Decimal('220'),
            'category': category2,
            'brand': brand2,
            'unit': 'ตัว',
            'description': 'เสื้อยืดแบรนด์ Apple'
        },
        {
            'name': 'หูฟัง Samsung Buds',
            'cost_price': Decimal('1500'),
            'price_a': Decimal('2500'),
            'price_aa': Decimal('2300'),
            'price_aaa': Decimal('2100'),
            'category': category1,
            'brand': brand1,
            'unit': 'คู่',
            'description': 'หูฟังไร้สาย Samsung'
        }
    ]

    for data in products_data:
        product = Product.objects.create(**data)
        profit_margin = 0
        if product.cost_price > 0 and product.price_a > 0:
            profit_margin = ((product.price_a - product.cost_price) / product.price_a) * 100
        print(f'สร้างสินค้า: {product.name}')
        print(f'  - ต้นทุน: {product.cost_price} บาท')
        print(f'  - ราคาขาย: {product.price_a} บาท') 
        print(f'  - กำไร: {profit_margin:.1f}%')
        print(f'  - SKU: {product.sku}')

    # สถิติ
    print(f'\n=== สถิติ ===')
    print(f'รวมสินค้าในระบบ: {Product.objects.count()}')
    print(f'รวม Category: {Category.objects.count()}')
    print(f'รวม Brand: {Brand.objects.count()}')
    print(f'สินค้าที่มี cost_price > 0: {Product.objects.filter(cost_price__gt=0).count()}')
    print(f'สินค้าที่มี price_a > 0: {Product.objects.filter(price_a__gt=0).count()}')
    
    # ทดสอบการคำนวณ profit
    from django.db.models import F, ExpressionWrapper, DecimalField
    top_profit_products = Product.objects.filter(
        cost_price__gt=0,
        price_a__gt=F('cost_price')
    ).annotate(
        profit_margin=ExpressionWrapper(
            ((F('price_a') - F('cost_price')) / F('price_a')) * 100,
            output_field=DecimalField(max_digits=5, decimal_places=2)
        )
    ).order_by('-profit_margin')[:5]
    
    print(f'\n=== สินค้ากำไรดี Top 5 ===')
    for product in top_profit_products:
        print(f'{product.name}: {product.profit_margin:.1f}%')

if __name__ == '__main__':
    create_sample_data()
