# ตัวอย่างการใช้ decorators เพื่อควบคุมสิทธิ์ใน views
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import Group

# วิธีที่ 1: ใช้ permission_required decorator
@login_required
@permission_required('App_Products.add_product', raise_exception=True)
def product_create(request):
    # เฉพาะผู้ที่มีสิทธิ์ add_product เท่านั้น
    pass

# วิธีที่ 2: ใช้ user_passes_test สำหรับเงื่อนไขซับซ้อน
def is_manager_or_admin(user):
    return user.groups.filter(name__in=['ผู้จัดการ (Manager)', 'ผู้ดูแลระบบ (Admin)']).exists()

@login_required
@user_passes_test(is_manager_or_admin)
def manager_report(request):
    # เฉพาะผู้จัดการและแอดมินเท่านั้น
    pass

# วิธีที่ 3: ตรวจสอบสิทธิ์ใน view function
@login_required
def purchase_approve(request, po_id):
    # ตรวจสอบสิทธิ์การอนุมัติ
    if not (request.user.groups.filter(name__in=['ผู้จัดการ (Manager)', 'นักบัญชี (Accountant)']).exists() 
            or request.user.is_superuser):
        messages.error(request, 'คุณไม่มีสิทธิ์ในการอนุมัติ')
        return redirect('purchase:list')
    
    # โค้ดสำหรับการอนุมัติ
    pass
