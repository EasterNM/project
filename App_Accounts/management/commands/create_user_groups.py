from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from App_Inventory.models import InventoryItem, Location
from App_Purchase.models import PurchaseOrder, PurchaseRequisition
from App_OrderingProductForSale.models import OrderRequest
from App_Products.models import Product, Category
from App_Supplier.models import Supplier
from App_Customer.models import Customer


class Command(BaseCommand):
    help = 'Create user groups and permissions for the system'

    def handle(self, *args, **options):
        # สร้าง Groups
        groups_data = [
            {
                'name': 'Inventory_Manager',
                'description': 'ผู้จัดการคลังสินค้า - จัดการคลังสินค้าทั้งหมด',
                'models': {
                    'inventory': ['view', 'add', 'change', 'delete'],
                    'location': ['view', 'add', 'change', 'delete'],
                    'product': ['view']
                }
            },
            {
                'name': 'Inventory_Staff',
                'description': 'พนักงานคลังสินค้า - ดูข้อมูลคลังสินค้า',
                'models': {
                    'inventory': ['view'],
                    'location': ['view'],
                    'product': ['view']
                }
            },
            {
                'name': 'Purchase_Manager',
                'description': 'ผู้จัดการจัดซื้อ - จัดการการจัดซื้อทั้งหมด',
                'models': {
                    'purchaseorder': ['view', 'add', 'change', 'delete'],
                    'purchaserequisition': ['view', 'add', 'change', 'delete'],
                    'supplier': ['view', 'add', 'change', 'delete']
                }
            },
            {
                'name': 'Purchase_Staff',
                'description': 'พนักงานจัดซื้อ - ดูข้อมูลการจัดซื้อ',
                'models': {
                    'purchaseorder': ['view'],
                    'purchaserequisition': ['view'],
                    'supplier': ['view']
                }
            },
            {
                'name': 'Sales_Manager',
                'description': 'ผู้จัดการขาย - จัดการการขายและลูกค้า',
                'models': {
                    'orderrequest': ['view', 'add', 'change', 'delete'],
                    'customer': ['view', 'add', 'change', 'delete'],
                    'product': ['view']
                }
            },
            {
                'name': 'Sales_Staff',
                'description': 'พนักงานขาย - ดูข้อมูลการขายและลูกค้า',
                'models': {
                    'orderrequest': ['view', 'add'],
                    'customer': ['view'],
                    'product': ['view']
                }
            },
            {
                'name': 'Product_Manager',
                'description': 'ผู้จัดการสินค้า - จัดการสินค้าและซัพพลายเออร์',
                'models': {
                    'product': ['view', 'add', 'change', 'delete'],
                    'category': ['view', 'add', 'change', 'delete'],
                    'supplier': ['view']
                }
            },
            {
                'name': 'Product_Staff',
                'description': 'พนักงานสินค้า - ดูข้อมูลสินค้า',
                'models': {
                    'product': ['view'],
                    'category': ['view']
                }
            },
            {
                'name': 'Finance_Manager',
                'description': 'ผู้จัดการการเงิน - ดูข้อมูลการเงินทั้งหมด',
                'models': {
                    'orderrequest': ['view'],
                    'purchaseorder': ['view'],
                    'customer': ['view'],
                    'supplier': ['view']
                }
            },
            {
                'name': 'Finance_Staff',
                'description': 'พนักงานการเงิน - ดูข้อมูลการเงินบางส่วน',
                'models': {
                    'orderrequest': ['view'],
                    'purchaseorder': ['view']
                }
            },
            {
                'name': 'Readonly_User',
                'description': 'ผู้ใช้อ่านอย่างเดียว - ดูข้อมูลได้ทั้งหมดแต่ไม่สามารถแก้ไข',
                'models': {
                    'inventory': ['view'],
                    'location': ['view'],
                    'purchaseorder': ['view'],
                    'purchaserequisition': ['view'],
                    'orderrequest': ['view'],
                    'product': ['view'],
                    'category': ['view'],
                    'supplier': ['view'],
                    'customer': ['view']
                }
            },
            {
                'name': 'Limited_User',
                'description': 'ผู้ใช้จำกัด - เข้าได้เฉพาะหน้าหลัก',
                'models': {}
            }
        ]

        # ContentType mapping
        model_content_types = {
            'inventory': ContentType.objects.get_for_model(InventoryItem),
            'location': ContentType.objects.get_for_model(Location),
            'purchaseorder': ContentType.objects.get_for_model(PurchaseOrder),
            'purchaserequisition': ContentType.objects.get_for_model(PurchaseRequisition),
            'orderrequest': ContentType.objects.get_for_model(OrderRequest),
            'product': ContentType.objects.get_for_model(Product),
            'category': ContentType.objects.get_for_model(Category),
            'supplier': ContentType.objects.get_for_model(Supplier),
            'customer': ContentType.objects.get_for_model(Customer)
        }

        created_groups = []
        for group_data in groups_data:
            group, created = Group.objects.get_or_create(name=group_data['name'])
            
            # กำหนดสิทธิ์ตามโมเดล
            for model_name, actions in group_data.get('models', {}).items():
                if model_name in model_content_types:
                    content_type = model_content_types[model_name]
                    
                    for action in actions:
                        # สร้างชื่อสิทธิ์ เช่น 'view_inventoryitem', 'add_product', ฯลฯ
                        codename = f"{action}_{content_type.model}"
                        try:
                            perm = Permission.objects.get(
                                content_type=content_type,
                                codename=codename
                            )
                            group.permissions.add(perm)
                        except Permission.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"Permission {codename} does not exist")
                            )
            
            if created:
                created_groups.append(group_data['name'])
                self.stdout.write(
                    self.style.SUCCESS(f'Created group: {group_data["name"]} - {group_data["description"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Group already exists: {group_data["name"]}, updated permissions')
                )

        if created_groups:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {len(created_groups)} groups')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No new groups were created, but permissions may have been updated')
            )
            
        self.stdout.write(
            self.style.SUCCESS('\nGroups created/updated successfully! You can now assign users to these groups in Django Admin.')
        )
        self.stdout.write(
            self.style.SUCCESS('Go to: Admin Panel > Authentication and Authorization > Groups')
        )
