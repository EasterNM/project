from django import template
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

register = template.Library()

@register.filter
def has_permission(user, permission_codename):
    """
    ตรวจสอบว่าผู้ใช้มีสิทธิ์หรือไม่
    ใช้งาน: {% if user|has_permission:"add_product" %}
    """
    if user.is_superuser:
        return True
    return user.has_perm(permission_codename)

@register.filter
def in_group(user, group_name):
    """
    ตรวจสอบว่าผู้ใช้อยู่ในกลุ่มหรือไม่
    ใช้งาน: {% if user|in_group:"Manager" %}
    """
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()

@register.filter
def can_view_module(user, module_name):
    """
    ตรวจสอบว่าผู้ใช้สามารถเข้าดูโมดูลได้หรือไม่
    ใช้งาน: {% if user|can_view_module:"products" %}
    """
    if user.is_superuser:
        return True
    
    module_permissions = {
        'dashboard': ['view_dashboard'],
        'products': ['App_Products.view_product', 'App_Products.add_product', 'App_Products.change_product'],
        'inventory': ['App_Inventory.view_inventoryitem', 'App_Inventory.add_inventoryitem', 'App_Inventory.change_inventoryitem'],
        'purchase': ['App_Purchase.view_purchaserequisition', 'App_Purchase.view_purchaseorder'],
        'orders': ['App_OrderingProductForSale.view_orderrequest', 'App_OrderingProductForSale.add_orderrequest'],
        'customers': ['App_Customer.view_customer', 'App_Customer.add_customer'],
        'suppliers': ['App_Supplier.view_supplier', 'App_Supplier.add_supplier'],
    }
    
    permissions = module_permissions.get(module_name, [])
    return any(user.has_perm(perm) for perm in permissions)

@register.filter
def can_create(user, model_name):
    """
    ตรวจสอบว่าผู้ใช้สามารถสร้างรายการใหม่ได้หรือไม่
    ใช้งาน: {% if user|can_create:"product" %}
    """
    if user.is_superuser:
        return True
    return user.has_perm(f'{model_name.split(".")[0]}.add_{model_name.split(".")[-1]}')

@register.filter
def can_edit(user, model_name):
    """
    ตรวจสอบว่าผู้ใช้สามารถแก้ไขได้หรือไม่
    ใช้งาน: {% if user|can_edit:"product" %}
    """
    if user.is_superuser:
        return True
    return user.has_perm(f'{model_name.split(".")[0]}.change_{model_name.split(".")[-1]}')

@register.filter
def can_delete(user, model_name):
    """
    ตรวจสอบว่าผู้ใช้สามารถลบได้หรือไม่
    ใช้งาน: {% if user|can_delete:"product" %}
    """
    if user.is_superuser:
        return True
    return user.has_perm(f'{model_name.split(".")[0]}.delete_{model_name.split(".")[-1]}')

@register.filter
def user_role_display(user):
    """
    แสดงบทบาทของผู้ใช้
    ใช้งาน: {{ user|user_role_display }}
    """
    if user.is_superuser:
        return "ผู้ดูแลระบบ"
    
    roles = []
    for group in user.groups.all():
        roles.append(group.name)
    
    return ", ".join(roles) if roles else "ผู้ใช้ทั่วไป"

@register.filter
def user_role_badge_class(user):
    """
    คลาส CSS สำหรับ badge ตามบทบาท
    ใช้งาน: <span class="{{ user|user_role_badge_class }}">
    """
    if user.is_superuser:
        return "bg-red-100 text-red-800"
    
    group_classes = {
        'Manager': 'bg-purple-100 text-purple-800',
        'Staff': 'bg-blue-100 text-blue-800',
        'Warehouse': 'bg-green-100 text-green-800',
        'Sales': 'bg-yellow-100 text-yellow-800',
        'Accountant': 'bg-gray-100 text-gray-800',
        'Viewer': 'bg-indigo-100 text-indigo-800',
    }
    
    for group in user.groups.all():
        if group.name in group_classes:
            return group_classes[group.name]
    
    return "bg-gray-100 text-gray-600"

@register.inclusion_tag('components/user_role_badge.html')
def user_role_badge(user):
    """
    Component สำหรับแสดง badge บทบาทผู้ใช้
    ใช้งาน: {% user_role_badge user %}
    """
    return {
        'user': user,
        'role_display': user_role_display(user),
        'badge_class': user_role_badge_class(user)
    }

@register.simple_tag
def check_module_access(user, module_name):
    """
    ตรวจสอบการเข้าถึงโมดูลและส่งคืนข้อมูลสิทธิ์
    ใช้งาน: {% check_module_access user "products" as product_access %}
    """
    if user.is_superuser:
        return {
            'can_view': True,
            'can_create': True,
            'can_edit': True,
            'can_delete': True,
            'can_export': True
        }
    
    module_perms = {
        'products': {
            'can_view': user.has_perm('App_Products.view_product'),
            'can_create': user.has_perm('App_Products.add_product'),
            'can_edit': user.has_perm('App_Products.change_product'),
            'can_delete': user.has_perm('App_Products.delete_product'),
            'can_export': user.has_perm('App_Products.view_product'),
        },
        'inventory': {
            'can_view': user.has_perm('App_Inventory.view_inventoryitem'),
            'can_create': user.has_perm('App_Inventory.add_inventoryitem'),
            'can_edit': user.has_perm('App_Inventory.change_inventoryitem'),
            'can_delete': user.has_perm('App_Inventory.delete_inventoryitem'),
            'can_export': user.has_perm('App_Inventory.view_inventoryitem'),
        },
        'purchase': {
            'can_view': user.has_perm('App_Purchase.view_purchaserequisition'),
            'can_create': user.has_perm('App_Purchase.add_purchaserequisition'),
            'can_edit': user.has_perm('App_Purchase.change_purchaserequisition'),
            'can_delete': user.has_perm('App_Purchase.delete_purchaserequisition'),
            'can_approve': user.groups.filter(name__in=['Manager', 'Accountant']).exists(),
        },
        'suppliers': {
            'can_view': user.has_perm('App_Supplier.view_supplier'),
            'can_create': user.has_perm('App_Supplier.add_supplier'),
            'can_edit': user.has_perm('App_Supplier.change_supplier'),
            'can_delete': user.has_perm('App_Supplier.delete_supplier'),
            'can_export': user.has_perm('App_Supplier.view_supplier'),
        },
        'customers': {
            'can_view': user.has_perm('App_Customer.view_customer'),
            'can_create': user.has_perm('App_Customer.add_customer'),
            'can_edit': user.has_perm('App_Customer.change_customer'),
            'can_delete': user.has_perm('App_Customer.delete_customer'),
            'can_export': user.has_perm('App_Customer.view_customer'),
        }
    }
    
    return module_perms.get(module_name, {
        'can_view': False,
        'can_create': False,
        'can_edit': False,
        'can_delete': False,
        'can_export': False
    })
