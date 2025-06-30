"""
Context processors สำหรับจัดการสิทธิ์ผู้ใช้งาน
"""

def user_permissions(request):
    """
    Context processor เพื่อตรวจสอบสิทธิ์ผู้ใช้งานและแผนกของผู้ใช้
    อ่านสิทธิ์จาก Django Groups
    """
    if not request.user.is_authenticated:
        return {}

    user = request.user
    
    # ตรวจสอบสิทธิ์ตามแผนก
    user_department = user.department.name if user.department else None
    
    # สิทธิ์พื้นฐาน
    permissions = {
        # สิทธิ์พื้นฐาน - ทุกคนที่ login ได้
        'can_view_dashboard': True,
        
        # สิทธิ์ตามระดับ Staff/Superuser
        'can_manage_inventory': user.is_staff or user.is_superuser,
        'can_manage_purchase': user.is_staff or user.is_superuser,
        'can_manage_orders': user.is_staff or user.is_superuser,
        'can_manage_products': user.is_staff or user.is_superuser,
        'can_manage_suppliers': user.is_staff or user.is_superuser,
        'can_manage_customers': user.is_staff or user.is_superuser,
        
        # สิทธิ์การเข้าถึงหน้า
        'can_view_inventory': user.is_staff or user.is_superuser,
        'can_view_purchase': user.is_staff or user.is_superuser, 
        'can_view_orders': user.is_staff or user.is_superuser,
        'can_view_products': user.is_staff or user.is_superuser,
        'can_view_suppliers': user.is_staff or user.is_superuser,
        'can_view_customers': user.is_staff or user.is_superuser,
        
        # สิทธิ์พิเศษตามตำแหน่ง
        'is_manager': user.is_staff or user.is_superuser or (user.position and 'ผู้จัดการ' in user.position.name),
        'is_supervisor': user.is_staff or user.is_superuser or (user.position and ('ผู้จัดการ' in user.position.name or 'หัวหน้า' in user.position.name)),
        
        # ข้อมูลผู้ใช้
        'user_department': user_department,
        'user_position': user.position.name if user.position else None,
        'user_groups': [group.name for group in user.groups.all()],
    }
    
    # ตรวจสอบสิทธิ์จาก Groups
    user_groups = [group.name for group in user.groups.all()]
    
    # เพิ่มสิทธิ์ตาม Groups ที่มีในระบบ
    # Inventory Groups
    if 'Inventory_Manager' in user_groups:
        permissions['can_manage_inventory'] = True
        permissions['can_view_inventory'] = True
    
    if 'Inventory_Staff' in user_groups:
        permissions['can_view_inventory'] = True
    
    # Purchase Groups
    if 'Purchase_Manager' in user_groups:
        permissions['can_manage_purchase'] = True
        permissions['can_view_purchase'] = True
    
    if 'Purchase_Staff' in user_groups:
        permissions['can_view_purchase'] = True
    
    # Sales Groups
    if 'Sales_Manager' in user_groups:
        permissions['can_manage_orders'] = True
        permissions['can_manage_customers'] = True
        permissions['can_view_orders'] = True
        permissions['can_view_customers'] = True
    
    if 'Sales_Staff' in user_groups:
        permissions['can_view_orders'] = True
        permissions['can_view_customers'] = True
    
    # Product Groups
    if 'Product_Manager' in user_groups:
        permissions['can_manage_products'] = True
        permissions['can_manage_suppliers'] = True
        permissions['can_view_products'] = True
        permissions['can_view_suppliers'] = True
    
    if 'Product_Staff' in user_groups:
        permissions['can_view_products'] = True
    
    # Finance Groups
    if 'Finance_Manager' in user_groups or 'Finance_Staff' in user_groups:
        permissions['can_view_orders'] = True
        permissions['can_view_purchase'] = True
    
    # Readonly users
    if 'Readonly_User' in user_groups:
        for key in permissions:
            if key.startswith('can_view_'):
                permissions[key] = True
            elif key.startswith('can_manage_'):
                permissions[key] = False
    
    # Limited users
    if 'Limited_User' in user_groups:
        for key in permissions:
            if key != 'can_view_dashboard' and key.startswith(('can_view_', 'can_manage_')):
                permissions[key] = False
    
    return {'user_perms': permissions}
