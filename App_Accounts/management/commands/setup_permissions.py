from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

class Command(BaseCommand):
    help = 'สร้าง Groups และ Permissions สำหรับระบบ Storems'

    def handle(self, *args, **options):
        self.stdout.write('🚀 เริ่มสร้าง Groups และ Permissions...')
        
        # ข้อมูล Groups และสิทธิ์
        groups_data = {
            'ผู้ดูแลระบบ (Admin)': {
                'description': 'ผู้ดูแลระบบมีสิทธิ์ทั้งหมด',
                'permissions': ['*']  # ทุกสิทธิ์
            },
            'ผู้จัดการ (Manager)': {
                'description': 'ผู้จัดการสามารถดู แก้ไข และอนุมัติได้',
                'permissions': [
                    # Dashboard
                    'view_dashboard',
                    # Products
                    'App_Products.view_product',
                    'App_Products.add_product', 
                    'App_Products.change_product',
                    'App_Products.delete_product',
                    # Inventory
                    'App_Inventory.view_inventoryitem',
                    'App_Inventory.add_inventoryitem',
                    'App_Inventory.change_inventoryitem',
                    'App_Inventory.delete_inventoryitem',
                    # Purchase
                    'App_Purchase.view_purchaserequisition',
                    'App_Purchase.add_purchaserequisition',
                    'App_Purchase.change_purchaserequisition',
                    'App_Purchase.view_purchaseorder',
                    'App_Purchase.add_purchaseorder',
                    'App_Purchase.change_purchaseorder',
                    # Suppliers
                    'App_Supplier.view_supplier',
                    'App_Supplier.add_supplier',
                    'App_Supplier.change_supplier',
                    'App_Supplier.delete_supplier',
                    # Customers
                    'App_Customer.view_customer',
                    'App_Customer.add_customer',
                    'App_Customer.change_customer',
                    'App_Customer.delete_customer',
                    # Orders
                    'App_OrderingProductForSale.view_orderrequest',
                    'App_OrderingProductForSale.add_orderrequest',
                    'App_OrderingProductForSale.change_orderrequest',
                    'App_OrderingProductForSale.delete_orderrequest',
                ]
            },
            'พนักงานคลัง (Warehouse Staff)': {
                'description': 'พนักงานคลังสามารถจัดการสินค้าและสต็อกได้',
                'permissions': [
                    'view_dashboard',
                    # Products - ดูและแก้ไข
                    'App_Products.view_product',
                    'App_Products.change_product',
                    # Inventory - ทุกสิทธิ์
                    'App_Inventory.view_inventoryitem',
                    'App_Inventory.add_inventoryitem',
                    'App_Inventory.change_inventoryitem',
                    # Purchase - ดูและสร้าง PR
                    'App_Purchase.view_purchaserequisition',
                    'App_Purchase.add_purchaserequisition',
                    'App_Purchase.view_purchaseorder',
                    # Orders - ดูและปรับสถานะ
                    'App_OrderingProductForSale.view_orderrequest',
                    'App_OrderingProductForSale.change_orderrequest',
                ]
            },
            'พนักงานขาย (Sales Staff)': {
                'description': 'พนักงานขายสามารถจัดการลูกค้าและออเดอร์ได้',
                'permissions': [
                    'view_dashboard',
                    # Products - ดูอย่างเดียว
                    'App_Products.view_product',
                    # Customers - ทุกสิทธิ์
                    'App_Customer.view_customer',
                    'App_Customer.add_customer',
                    'App_Customer.change_customer',
                    # Orders - ทุกสิทธิ์
                    'App_OrderingProductForSale.view_orderrequest',
                    'App_OrderingProductForSale.add_orderrequest',
                    'App_OrderingProductForSale.change_orderrequest',
                    # Inventory - ดูอย่างเดียว
                    'App_Inventory.view_inventoryitem',
                ]
            },
            'พนักงานจัดซื้อ (Purchasing Staff)': {
                'description': 'พนักงานจัดซื้อสามารถจัดการการสั่งซื้อได้',
                'permissions': [
                    'view_dashboard',
                    # Products - ดูและเพิ่ม
                    'App_Products.view_product',
                    'App_Products.add_product',
                    # Suppliers - ทุกสิทธิ์
                    'App_Supplier.view_supplier',
                    'App_Supplier.add_supplier',
                    'App_Supplier.change_supplier',
                    # Purchase - ทุกสิทธิ์
                    'App_Purchase.view_purchaserequisition',
                    'App_Purchase.add_purchaserequisition',
                    'App_Purchase.change_purchaserequisition',
                    'App_Purchase.view_purchaseorder',
                    'App_Purchase.add_purchaseorder',
                    'App_Purchase.change_purchaseorder',
                    # Inventory - ดูอย่างเดียว
                    'App_Inventory.view_inventoryitem',
                ]
            },
            'นักบัญชี (Accountant)': {
                'description': 'นักบัญชีสามารถดูรายงานและอนุมัติการเงินได้',
                'permissions': [
                    'view_dashboard',
                    # ดูข้อมูลทั้งหมด
                    'App_Products.view_product',
                    'App_Inventory.view_inventoryitem',
                    'App_Purchase.view_purchaserequisition',
                    'App_Purchase.view_purchaseorder',
                    'App_Supplier.view_supplier',
                    'App_Customer.view_customer',
                    'App_OrderingProductForSale.view_orderrequest',
                    # อนุมัติการสั่งซื้อ
                    'purchase.change_purchaseorder',
                ]
            },
            'ผู้ดู (Viewer)': {
                'description': 'ผู้ดูสามารถดูข้อมูลอย่างเดียว',
                'permissions': [
                    'view_dashboard',
                    'App_Products.view_product',
                    'App_Inventory.view_inventoryitem',
                    'App_Purchase.view_purchaserequisition',
                    'App_Purchase.view_purchaseorder',
                    'App_Supplier.view_supplier',
                    'App_Customer.view_customer',
                    'App_OrderingProductForSale.view_orderrequest',
                ]
            }
        }
        
        # สร้าง Groups
        for group_name, data in groups_data.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                self.stdout.write(f'✅ สร้าง Group: {group_name}')
            else:
                self.stdout.write(f'📝 อัปเดต Group: {group_name}')
            
            # ล้างสิทธิ์เดิม
            group.permissions.clear()
            
            # เพิ่มสิทธิ์
            if data['permissions'] == ['*']:
                # ให้สิทธิ์ทั้งหมด (สำหรับ Admin)
                all_permissions = Permission.objects.all()
                group.permissions.set(all_permissions)
                self.stdout.write(f'   ➡️  เพิ่มสิทธิ์ทั้งหมด ({all_permissions.count()} สิทธิ์)')
            else:
                # เพิ่มสิทธิ์ตามที่กำหนด
                added_count = 0
                for perm_code in data['permissions']:
                    if perm_code == 'view_dashboard':
                        # สร้างสิทธิ์พิเศษสำหรับ dashboard
                        continue
                    
                    try:
                        if '.' in perm_code:
                            app_label, codename = perm_code.split('.')
                            permission = Permission.objects.get(
                                content_type__app_label=app_label,
                                codename=codename
                            )
                        else:
                            permission = Permission.objects.get(codename=perm_code)
                        
                        group.permissions.add(permission)
                        added_count += 1
                    except Permission.DoesNotExist:
                        self.stdout.write(f'   ⚠️  ไม่พบสิทธิ์: {perm_code}')
                
                self.stdout.write(f'   ➡️  เพิ่มสิทธิ์: {added_count} สิทธิ์')
        
        # สร้างสิทธิ์พิเศษ (ถ้าต้องการ)
        self.create_custom_permissions()
        
        self.stdout.write('🎉 สร้าง Groups และ Permissions เสร็จสิ้น!')
        self.stdout.write('')
        self.stdout.write('📋 Groups ที่สร้าง:')
        for group in Group.objects.all():
            self.stdout.write(f'   • {group.name} ({group.permissions.count()} สิทธิ์)')
        
        self.stdout.write('')
        self.stdout.write('🔧 วิธีใช้งาน:')
        self.stdout.write('   1. ไปที่ Django Admin → Groups')
        self.stdout.write('   2. ไปที่ Django Admin → Users')
        self.stdout.write('   3. เพิ่มผู้ใช้เข้า Groups ที่เหมาะสม')

    def create_custom_permissions(self):
        """สร้างสิทธิ์พิเศษ"""
        # สร้าง ContentType สำหรับสิทธิ์พิเศษ
        try:
            from django.contrib.auth.models import User
            content_type = ContentType.objects.get_for_model(User)
            
            custom_permissions = [
                ('view_dashboard', 'สามารถเข้าถึงหน้า Dashboard'),
                ('approve_purchase', 'สามารถอนุมัติการสั่งซื้อ'),
                ('export_data', 'สามารถ Export ข้อมูล'),
                ('view_reports', 'สามารถดูรายงาน'),
            ]
            
            for codename, name in custom_permissions:
                permission, created = Permission.objects.get_or_create(
                    codename=codename,
                    name=name,
                    content_type=content_type,
                )
                if created:
                    self.stdout.write(f'   ✅ สร้างสิทธิ์พิเศษ: {name}')
        except Exception as e:
            self.stdout.write(f'   ⚠️  ไม่สามารถสร้างสิทธิ์พิเศษได้: {e}')
