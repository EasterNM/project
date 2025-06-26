from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q, F
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import (
    PurchaseRequisition, PurchaseRequisitionDetail,
    PurchaseOrder, PurchaseOrderDetail,
    GoodsReceipt, GoodsReceiptDetail
)
from App_Products.models import Product
from App_Supplier.models import Supplier
from App_Inventory.models import Location, InventoryItem

# ==============================================
# Dashboard View
# ==============================================

@login_required
def purchase_dashboard(request):
    """Dashboard แสดงภาพรวมของการจัดซื้อ"""
    
    # นับจำนวน PR ตามสถานะ
    pr_stats = {
        'draft': PurchaseRequisition.objects.filter(status=PurchaseRequisition.Status.DRAFT).count(),
        'pending': PurchaseRequisition.objects.filter(status=PurchaseRequisition.Status.PENDING).count(),
        'approved': PurchaseRequisition.objects.filter(status=PurchaseRequisition.Status.APPROVED).count(),
        'rejected': PurchaseRequisition.objects.filter(
            status__in=[
                PurchaseRequisition.Status.REJECTED,
                PurchaseRequisition.Status.CANCELLED
            ]
        ).count(),
        'total': PurchaseRequisition.objects.count(),
    }
    
    # นับจำนวน PO ตามสถานะ
    po_stats = {
        'draft': PurchaseOrder.objects.filter(status=PurchaseOrder.Status.DRAFT).count(),
        'pending': PurchaseOrder.objects.filter(status=PurchaseOrder.Status.PENDING).count(),
        'approved': PurchaseOrder.objects.filter(
            status__in=[
                PurchaseOrder.Status.APPROVED, 
                PurchaseOrder.Status.PARTIALLY_RECEIVED
            ]
        ).count(),
        'completed': PurchaseOrder.objects.filter(status=PurchaseOrder.Status.FULLY_RECEIVED).count(),
        'total': PurchaseOrder.objects.count(),
    }
    
    # PO ล่าสุดที่ยังไม่ได้รับสินค้า
    recent_pos = PurchaseOrder.objects.filter(
        status__in=[
            PurchaseOrder.Status.APPROVED, 
            PurchaseOrder.Status.PARTIALLY_RECEIVED
        ]
    ).order_by('-order_date')[:5]
    
    # การรับสินค้าล่าสุด
    recent_receipts = GoodsReceipt.objects.order_by('-receipt_date')[:5]
    
    # สินค้าที่มีการซื้อบ่อยที่สุด
    top_products = Product.objects.annotate(
        po_count=Count('purchaseorderdetail')
    ).order_by('-po_count')[:5]
    
    # รายการใบขอซื้อที่รออนุมัติ
    pending_requisitions = PurchaseRequisition.objects.filter(
        status=PurchaseRequisition.Status.PENDING
    ).order_by('-request_date')[:5]
    
    # รายการใบสั่งซื้อที่รออนุมัติ
    pending_orders = PurchaseOrder.objects.filter(
        status=PurchaseOrder.Status.PENDING
    ).order_by('-order_date')[:5]
    
    context = {
        'pr_stats': pr_stats,
        'po_stats': po_stats,
        'recent_pos': recent_pos,
        'recent_receipts': recent_receipts,
        'top_products': top_products,
        'pending_requisitions': pending_requisitions,
        'pending_orders': pending_orders,
    }
    
    return render(request, 'purchase/dashboard.html', context)

# ==============================================
# Purchase Requisition Views
# ==============================================

@login_required
def requisition_list(request):
    """แสดงรายการใบขอซื้อทั้งหมด"""
    # Get query parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Start with all requisitions
    requisitions = PurchaseRequisition.objects.all()
    
    # Apply filters
    if status_filter:
        requisitions = requisitions.filter(status=status_filter)
    
    if search_query:
        requisitions = requisitions.filter(
            Q(pr_number__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(requested_by__username__icontains=search_query)
        )
    
    # Order by most recent
    requisitions = requisitions.order_by('-request_date')
    
    context = {
        'requisitions': requisitions,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': PurchaseRequisition.Status.choices
    }
    
    return render(request, 'purchase/requisition_list.html', context)

@login_required
def requisition_detail(request, pr_number):
    """แสดงรายละเอียดของใบขอซื้อ"""
    requisition = get_object_or_404(PurchaseRequisition, pr_number=pr_number)
    
    # Check if this PR has been converted to PO
    has_po = requisition.purchase_orders.exists()
    
    context = {
        'requisition': requisition,
        'details': requisition.details.all(),
        'has_po': has_po
    }
    
    return render(request, 'purchase/requisition_detail.html', context)

@login_required
def requisition_create(request):
    """สร้างใบขอซื้อใหม่"""
    products = Product.objects.all().order_by('name')
    
    if request.method == 'POST':
        # Get form data
        department = request.POST.get('department')
        required_date = request.POST.get('required_date')
        remarks = request.POST.get('remarks', '')
        status = request.POST.get('status', PurchaseRequisition.Status.DRAFT)
        
        # Get product details from form
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        descriptions = request.POST.getlist('description')
        
        if department and required_date and product_ids and quantities:
            try:
                with transaction.atomic():
                    # Create PR
                    pr = PurchaseRequisition.objects.create(
                        requested_by=request.user,
                        department=department,
                        required_date=required_date,
                        remarks=remarks,
                        status=status
                    )
                    
                    # Create PR details
                    for i, product_id in enumerate(product_ids):
                        if product_id and int(quantities[i]) > 0:
                            product = Product.objects.get(id=product_id)
                            description = descriptions[i] if i < len(descriptions) else ''
                            
                            PurchaseRequisitionDetail.objects.create(
                                purchase_requisition=pr,
                                product=product,
                                quantity=quantities[i],
                                description=description
                            )
                    
                    messages.success(request, f'สร้างใบขอซื้อ {pr.pr_number} เรียบร้อยแล้ว')
                    return redirect('purchase:requisition_detail', pr_number=pr.pr_number)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    context = {
        'products': products,
        'today': timezone.now().date(),
    }
    
    return render(request, 'purchase/requisition_form.html', context)

@login_required
def requisition_edit(request, pr_number):
    """แก้ไขใบขอซื้อที่ยังไม่ได้อนุมัติ"""
    requisition = get_object_or_404(PurchaseRequisition, pr_number=pr_number)
    
    # Only allow editing of draft PRs
    if requisition.status != PurchaseRequisition.Status.DRAFT:
        messages.error(request, 'ไม่สามารถแก้ไขใบขอซื้อที่ไม่ได้อยู่ในสถานะฉบับร่าง')
        return redirect('purchase:requisition_detail', pr_number=pr_number)
    
    products = Product.objects.all().order_by('name')
    
    if request.method == 'POST':
        # Get form data
        department = request.POST.get('department')
        required_date = request.POST.get('required_date')
        remarks = request.POST.get('remarks', '')
        status = request.POST.get('status', PurchaseRequisition.Status.DRAFT)
        
        # Get product details from form
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        descriptions = request.POST.getlist('description')
        detail_ids = request.POST.getlist('detail_id')
        
        if department and required_date and product_ids and quantities:
            try:
                with transaction.atomic():
                    # Update PR
                    requisition.department = department
                    requisition.required_date = required_date
                    requisition.remarks = remarks
                    requisition.status = status
                    requisition.save()
                    
                    # Keep track of detail IDs we've processed
                    processed_details = []
                    
                    # Update or create PR details
                    for i, product_id in enumerate(product_ids):
                        if product_id and int(quantities[i]) > 0:
                            product = Product.objects.get(id=product_id)
                            description = descriptions[i] if i < len(descriptions) else ''
                            
                            # If detail_id is provided, update existing detail
                            if i < len(detail_ids) and detail_ids[i]:
                                detail_id = int(detail_ids[i])
                                detail = PurchaseRequisitionDetail.objects.get(id=detail_id)
                                detail.product = product
                                detail.quantity = quantities[i]
                                detail.description = description
                                detail.save()
                                processed_details.append(detail_id)
                            else:
                                # Create new detail
                                detail = PurchaseRequisitionDetail.objects.create(
                                    purchase_requisition=requisition,
                                    product=product,
                                    quantity=quantities[i],
                                    description=description
                                )
                                processed_details.append(detail.id)
                    
                    # Delete details that weren't processed (removed by the user)
                    requisition.details.exclude(id__in=processed_details).delete()
                    
                    messages.success(request, f'อัปเดตใบขอซื้อ {requisition.pr_number} เรียบร้อยแล้ว')
                    return redirect('purchase:requisition_detail', pr_number=requisition.pr_number)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    context = {
        'requisition': requisition,
        'details': requisition.details.all(),
        'products': products,
        'today': timezone.now().date(),
    }
    
    return render(request, 'purchase/requisition_form.html', context)

@login_required
def requisition_approve(request, pr_number):
    """อนุมัติหรือปฏิเสธใบขอซื้อ"""
    requisition = get_object_or_404(PurchaseRequisition, pr_number=pr_number)
    
    # ตรวจสอบว่าใบขอซื้ออยู่ในสถานะที่เหมาะสมสำหรับการอนุมัติ
    if requisition.status != PurchaseRequisition.Status.PENDING:
        messages.error(request, 'สามารถอนุมัติได้เฉพาะใบขอซื้อที่อยู่ในสถานะรออนุมัติเท่านั้น')
        return redirect('purchase:requisition_detail', pr_number=pr_number)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')
        
        if action == 'approve':
            requisition.status = PurchaseRequisition.Status.APPROVED
            success_message = f'อนุมัติใบขอซื้อ {pr_number} เรียบร้อยแล้ว'
        elif action == 'reject':
            requisition.status = PurchaseRequisition.Status.REJECTED
            success_message = f'ปฏิเสธใบขอซื้อ {pr_number} เรียบร้อยแล้ว'
        else:
            messages.error(request, 'ระบุการกระทำไม่ถูกต้อง')
            return redirect('purchase:requisition_detail', pr_number=pr_number)
        
        # บันทึกเหตุผลในหมายเหตุ
        if reason:
            requisition.remarks = f"{requisition.remarks}\n\nการอนุมัติ/ปฏิเสธ: {reason}"
        
        # บันทึกการเปลี่ยนแปลง
        try:
            requisition.save()
            messages.success(request, success_message)
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            
        return redirect('purchase:requisition_detail', pr_number=pr_number)
    
    context = {
        'requisition': requisition,
        'details': requisition.details.all(),
    }
    
    return render(request, 'purchase/requisition_approve.html', context)

@login_required
def requisition_cancel(request, pr_number):
    """ยกเลิกใบขอซื้อ"""
    requisition = get_object_or_404(PurchaseRequisition, pr_number=pr_number)
    
    # ตรวจสอบว่าสามารถยกเลิกได้หรือไม่
    # ไม่สามารถยกเลิกได้หากถูกแปลงเป็นใบสั่งซื้อแล้ว
    if requisition.status == PurchaseRequisition.Status.CONVERTED:
        messages.error(request, 'ไม่สามารถยกเลิกใบขอซื้อที่ถูกแปลงเป็นใบสั่งซื้อแล้ว')
        return redirect('purchase:requisition_detail', pr_number=pr_number)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # เปลี่ยนสถานะเป็นยกเลิก
        requisition.status = PurchaseRequisition.Status.CANCELLED
        
        # บันทึกเหตุผลในหมายเหตุ
        if reason:
            requisition.remarks = f"{requisition.remarks}\n\nเหตุผลที่ยกเลิก: {reason}"
        
        # บันทึกการเปลี่ยนแปลง
        try:
            requisition.save()
            messages.success(request, f'ยกเลิกใบขอซื้อ {pr_number} เรียบร้อยแล้ว')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            
        return redirect('purchase:requisition_detail', pr_number=pr_number)
    
    context = {
        'requisition': requisition,
    }
    
    return render(request, 'purchase/requisition_cancel.html', context)

# ==============================================
# Purchase Order Views
# ==============================================

@login_required
def order_list(request):
    """แสดงรายการใบสั่งซื้อทั้งหมด"""
    # Get query parameters
    status_filter = request.GET.get('status', '')
    supplier_filter = request.GET.get('supplier', '')
    search_query = request.GET.get('search', '')
    
    # Start with all orders
    orders = PurchaseOrder.objects.all()
    
    # Apply filters
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if supplier_filter:
        orders = orders.filter(supplier_id=supplier_filter)
    
    if search_query:
        orders = orders.filter(
            Q(po_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(purchase_requisition__pr_number__icontains=search_query)
        )
    
    # Order by most recent
    orders = orders.order_by('-order_date')
    
    # Get suppliers for filter dropdown
    suppliers = Supplier.objects.filter(status=Supplier.Status.ACTIVE).order_by('company_name')
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'supplier_filter': supplier_filter,
        'search_query': search_query,
        'suppliers': suppliers,
        'status_choices': PurchaseOrder.Status.choices
    }
    
    return render(request, 'purchase/order_list.html', context)

@login_required
def order_detail(request, po_number):
    """แสดงรายละเอียดของใบสั่งซื้อ"""
    order = get_object_or_404(PurchaseOrder, po_number=po_number)
    
    # Get receipts for this PO
    receipts = order.goods_receipts.all().order_by('-receipt_date')
    
    # Calculate received quantities for each item
    details = []
    for detail in order.details.all():
        received = detail.received_quantity
        remaining = detail.quantity - received
        
        details.append({
            'detail': detail,
            'received_quantity': received,
            'remaining_quantity': remaining
        })
    
    context = {
        'order': order,
        'details': details,
        'receipts': receipts,
        'can_receive': order.status in [
            PurchaseOrder.Status.APPROVED, 
            PurchaseOrder.Status.PARTIALLY_RECEIVED
        ]
    }
    
    return render(request, 'purchase/order_detail.html', context)

@login_required
def order_create(request):
    """สร้างใบสั่งซื้อใหม่ (Manual)"""
    suppliers = Supplier.objects.filter(status=Supplier.Status.ACTIVE).order_by('company_name')
    products = Product.objects.all().order_by('name')
    
    if request.method == 'POST':
        # Get form data
        supplier_id = request.POST.get('supplier')
        expected_delivery_date = request.POST.get('expected_delivery_date')
        status = request.POST.get('status', PurchaseOrder.Status.DRAFT)
        
        # Get product details from form
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        unit_prices = request.POST.getlist('unit_price')
        
        if supplier_id and expected_delivery_date and product_ids and quantities and unit_prices:
            try:
                with transaction.atomic():
                    # Create PO
                    supplier = Supplier.objects.get(id=supplier_id)
                    po = PurchaseOrder.objects.create(
                        supplier=supplier,
                        expected_delivery_date=expected_delivery_date,
                        status=status,
                        created_by=request.user
                    )
                    
                    # Create PO details
                    for i, product_id in enumerate(product_ids):
                        if product_id and int(quantities[i]) > 0 and float(unit_prices[i]) > 0:
                            product = Product.objects.get(id=product_id)
                            
                            PurchaseOrderDetail.objects.create(
                                purchase_order=po,
                                product=product,
                                quantity=quantities[i],
                                unit_price=unit_prices[i]
                            )
                    
                    messages.success(request, f'สร้างใบสั่งซื้อ {po.po_number} เรียบร้อยแล้ว')
                    return redirect('purchase:order_detail', po_number=po.po_number)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    context = {
        'suppliers': suppliers,
        'products': products,
        'today': timezone.now().date(),
    }
    
    return render(request, 'purchase/order_form.html', context)

@login_required
def order_create_from_pr(request, pr_number):
    """สร้างใบสั่งซื้อจากใบขอซื้อ"""
    requisition = get_object_or_404(PurchaseRequisition, pr_number=pr_number)
    
    # Check if PR can be converted to PO
    if requisition.status != PurchaseRequisition.Status.APPROVED:
        messages.error(request, 'ใบขอซื้อต้องได้รับการอนุมัติก่อนจึงจะสร้างใบสั่งซื้อได้')
        return redirect('purchase:requisition_detail', pr_number=pr_number)
    
    suppliers = Supplier.objects.filter(status=Supplier.Status.ACTIVE).order_by('company_name')
    
    if request.method == 'POST':
        # Get form data
        supplier_id = request.POST.get('supplier')
        expected_delivery_date = request.POST.get('expected_delivery_date')
        status = request.POST.get('status', PurchaseOrder.Status.DRAFT)
        
        # Get product details from form
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        unit_prices = request.POST.getlist('unit_price')
        
        if supplier_id and expected_delivery_date and product_ids and quantities and unit_prices:
            try:
                with transaction.atomic():
                    # Create PO
                    supplier = Supplier.objects.get(id=supplier_id)
                    po = PurchaseOrder.objects.create(
                        supplier=supplier,
                        purchase_requisition=requisition,
                        expected_delivery_date=expected_delivery_date,
                        status=status,
                        created_by=request.user
                    )
                    
                    # Create PO details
                    any_valid_items = False
                    for i, product_id in enumerate(product_ids):
                        try:
                            if not product_id:
                                continue
                            
                            # Parse and validate quantity and price
                            try:
                                quantity = int(quantities[i])
                                unit_price = float(unit_prices[i])
                            except (ValueError, TypeError, IndexError):
                                messages.warning(request, f'ข้อมูลไม่ถูกต้องสำหรับสินค้าลำดับที่ {i+1}')
                                continue
                            
                            if quantity <= 0 or unit_price <= 0:
                                messages.warning(request, f'จำนวนหรือราคาต้องมากกว่า 0 สำหรับสินค้าลำดับที่ {i+1}')
                                continue
                            
                            product = Product.objects.get(id=product_id)
                            PurchaseOrderDetail.objects.create(
                                purchase_order=po,
                                product=product,
                                quantity=quantity,
                                unit_price=unit_price
                            )
                            any_valid_items = True
                        except Product.DoesNotExist:
                            messages.warning(request, f'ไม่พบข้อมูลสินค้าลำดับที่ {i+1}')
                            continue
                    
                    if not any_valid_items:
                        raise ValidationError('ไม่มีรายการสินค้าที่ถูกต้อง')
                    
                    # Update PR status to converted
                    requisition.status = PurchaseRequisition.Status.CONVERTED
                    requisition.save()
                    
                    messages.success(request, f'สร้างใบสั่งซื้อ {po.po_number} จากใบขอซื้อ {requisition.pr_number} เรียบร้อยแล้ว')
                    return redirect('purchase:order_detail', po_number=po.po_number)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    context = {
        'requisition': requisition,
        'details': requisition.details.all(),
        'suppliers': suppliers,
        'today': timezone.now().date(),
    }
    
    return render(request, 'purchase/order_form_from_pr.html', context)

@login_required
def order_edit(request, po_number):
    """แก้ไขใบสั่งซื้อที่ยังไม่ได้อนุมัติ"""
    order = get_object_or_404(PurchaseOrder, po_number=po_number)
    
    # Only allow editing of draft POs
    if order.status != PurchaseOrder.Status.DRAFT:
        messages.error(request, 'ไม่สามารถแก้ไขใบสั่งซื้อที่ไม่ได้อยู่ในสถานะร่าง')
        return redirect('purchase:order_detail', po_number=po_number)
    
    suppliers = Supplier.objects.filter(status=Supplier.Status.ACTIVE).order_by('company_name')
    products = Product.objects.all().order_by('name')
    
    if request.method == 'POST':
        # Get form data
        supplier_id = request.POST.get('supplier')
        expected_delivery_date = request.POST.get('expected_delivery_date')
        status = request.POST.get('status', PurchaseOrder.Status.DRAFT)
        
        # Get product details from form
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        unit_prices = request.POST.getlist('unit_price')
        detail_ids = request.POST.getlist('detail_id')
        
        if supplier_id and expected_delivery_date and product_ids and quantities and unit_prices:
            try:
                with transaction.atomic():
                    # Update PO
                    supplier = Supplier.objects.get(id=supplier_id)
                    order.supplier = supplier
                    order.expected_delivery_date = expected_delivery_date
                    order.status = status
                    order.save()
                    
                    # Keep track of detail IDs we've processed
                    processed_details = []
                    
                    # Update or create PO details
                    for i, product_id in enumerate(product_ids):
                        if product_id and int(quantities[i]) > 0 and float(unit_prices[i]) > 0:
                            product = Product.objects.get(id=product_id)
                            
                            # If detail_id is provided, update existing detail
                            if i < len(detail_ids) and detail_ids[i]:
                                detail_id = int(detail_ids[i])
                                detail = PurchaseOrderDetail.objects.get(id=detail_id)
                                detail.product = product
                                detail.quantity = quantities[i]
                                detail.unit_price = unit_prices[i]
                                detail.save()
                                processed_details.append(detail_id)
                            else:
                                # Create new detail
                                detail = PurchaseOrderDetail.objects.create(
                                    purchase_order=order,
                                    product=product,
                                    quantity=quantities[i],
                                    unit_price=unit_prices[i]
                                )
                                processed_details.append(detail.id)
                    
                    # Delete details that weren't processed (removed by the user)
                    order.details.exclude(id__in=processed_details).delete()
                    
                    messages.success(request, f'อัปเดตใบสั่งซื้อ {order.po_number} เรียบร้อยแล้ว')
                    return redirect('purchase:order_detail', po_number=order.po_number)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    context = {
        'order': order,
        'details': order.details.all(),
        'suppliers': suppliers,
        'products': products,
        'today': timezone.now().date(),
    }
    
    return render(request, 'purchase/order_form.html', context)

@login_required
def order_approve(request, po_number):
    """อนุมัติหรือปฏิเสธใบสั่งซื้อ"""
    order = get_object_or_404(PurchaseOrder, po_number=po_number)
    
    # ตรวจสอบว่าใบสั่งซื้ออยู่ในสถานะที่เหมาะสมสำหรับการอนุมัติ
    if order.status != PurchaseOrder.Status.PENDING:
        messages.error(request, 'สามารถอนุมัติได้เฉพาะใบสั่งซื้อที่อยู่ในสถานะรออนุมัติเท่านั้น')
        return redirect('purchase:order_detail', po_number=po_number)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            order.status = PurchaseOrder.Status.APPROVED
            success_message = f'อนุมัติใบสั่งซื้อ {po_number} เรียบร้อยแล้ว'
        elif action == 'reject':
            order.status = PurchaseOrder.Status.REJECTED
            success_message = f'ปฏิเสธใบสั่งซื้อ {po_number} เรียบร้อยแล้ว'
        else:
            messages.error(request, 'ระบุการกระทำไม่ถูกต้อง')
            return redirect('purchase:order_detail', po_number=po_number)
        
        # บันทึกการเปลี่ยนแปลง
        try:
            order.save()
            messages.success(request, success_message)
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            
        return redirect('purchase:order_detail', po_number=po_number)
    
    context = {
        'order': order,
        'details': order.details.all(),
    }
    
    return render(request, 'purchase/order_approve.html', context)

@login_required
def order_cancel(request, po_number):
    """ยกเลิกใบสั่งซื้อ"""
    order = get_object_or_404(PurchaseOrder, po_number=po_number)
    
    # ตรวจสอบว่าสามารถยกเลิกได้หรือไม่
    # ไม่สามารถยกเลิกได้หากมีการรับสินค้าแล้ว
    invalid_statuses = [
        PurchaseOrder.Status.PARTIALLY_RECEIVED,
        PurchaseOrder.Status.FULLY_RECEIVED
    ]
    
    if order.status in invalid_statuses:
        messages.error(request, 'ไม่สามารถยกเลิกใบสั่งซื้อที่มีการรับสินค้าแล้ว')
        return redirect('purchase:order_detail', po_number=po_number)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # เปลี่ยนสถานะเป็นยกเลิก
        order.status = PurchaseOrder.Status.CANCELLED
        
        # หากยกเลิก PO ที่มาจาก PR ให้เปลี่ยนสถานะ PR กลับเป็น APPROVED
        if order.purchase_requisition and order.purchase_requisition.status == PurchaseRequisition.Status.CONVERTED:
            order.purchase_requisition.status = PurchaseRequisition.Status.APPROVED
            order.purchase_requisition.save()
        
        # บันทึกการเปลี่ยนแปลง
        try:
            order.save()
            messages.success(request, f'ยกเลิกใบสั่งซื้อ {po_number} เรียบร้อยแล้ว')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            
        return redirect('purchase:order_detail', po_number=po_number)
    
    context = {
        'order': order,
    }
    
    return render(request, 'purchase/order_cancel.html', context)

# ==============================================
# Goods Receipt Views
# ==============================================

@login_required
def receipt_list(request):
    """แสดงรายการรับสินค้าทั้งหมด"""
    # Get query parameters
    po_filter = request.GET.get('po', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Start with all receipts
    receipts = GoodsReceipt.objects.all()
    
    # Apply filters
    if po_filter:
        receipts = receipts.filter(purchase_order__po_number__icontains=po_filter)
    
    if date_from:
        receipts = receipts.filter(receipt_date__gte=date_from)
    
    if date_to:
        receipts = receipts.filter(receipt_date__lte=date_to)
    
    # Order by most recent
    receipts = receipts.order_by('-receipt_date')
    
    context = {
        'receipts': receipts,
        'po_filter': po_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'purchase/receipt_list.html', context)

@login_required
def receipt_detail(request, receipt_id):
    """แสดงรายละเอียดการรับสินค้า"""
    receipt = get_object_or_404(GoodsReceipt, id=receipt_id)
    
    context = {
        'receipt': receipt,
        'details': receipt.details.all(),
    }
    
    return render(request, 'purchase/receipt_detail.html', context)

@login_required
def receipt_create(request, po_number):
    """รับสินค้าตามใบสั่งซื้อ"""
    order = get_object_or_404(PurchaseOrder, po_number=po_number)
    
    # Check if PO is in a state where goods can be received
    valid_statuses = [PurchaseOrder.Status.APPROVED, PurchaseOrder.Status.PARTIALLY_RECEIVED]
    if order.status not in valid_statuses:
        messages.error(request, 'ใบสั่งซื้อต้องได้รับการอนุมัติก่อนจึงจะรับสินค้าได้')
        return redirect('purchase:order_detail', po_number=po_number)
    
    # Get locations for storing received items
    locations = Location.objects.filter(is_active=True).order_by('location_name')
    
    # Get PO details with remaining quantities
    details = []
    for detail in order.details.all():
        received = detail.received_quantity
        remaining = detail.quantity - received
        
        if remaining > 0:
            details.append({
                'detail': detail,
                'received_quantity': received,
                'remaining_quantity': remaining
            })
    
    if request.method == 'POST':
        receipt_date = request.POST.get('receipt_date')
        notes = request.POST.get('notes', '')
        location_id = request.POST.get('location')
        
        # Get receipt details from form
        detail_ids = request.POST.getlist('detail_id')
        quantities = request.POST.getlist('quantity')
        conditions = request.POST.getlist('condition')
        lot_numbers = request.POST.getlist('lot_number')
        expiry_dates = request.POST.getlist('expiry_date')
        
        if receipt_date and location_id and detail_ids and quantities:
            try:
                with transaction.atomic():
                    # Create receipt
                    receipt = GoodsReceipt.objects.create(
                        purchase_order=order,
                        receipt_date=receipt_date,
                        received_by=request.user,
                        notes=notes
                    )
                    
                    # Create receipt details and inventory items
                    location = Location.objects.get(id=location_id)
                    has_items_received = False
                    
                    for i, detail_id in enumerate(detail_ids):
                        if int(quantities[i]) > 0:
                            po_detail = PurchaseOrderDetail.objects.get(id=detail_id)
                            condition = conditions[i] if i < len(conditions) else GoodsReceiptDetail.Condition.GOOD
                            
                            # ตรวจสอบว่าจำนวนที่รับไม่เกินจำนวนที่คงเหลือ
                            received = po_detail.received_quantity
                            remaining = po_detail.quantity - received
                            
                            if int(quantities[i]) > remaining:
                                raise ValidationError(f'จำนวนที่รับของสินค้า {po_detail.product.name} ({quantities[i]}) เกินกว่าจำนวนที่คงเหลือ ({remaining})')
                            
                            # Create receipt detail
                            receipt_detail = GoodsReceiptDetail.objects.create(
                                receipt=receipt,
                                purchase_order_detail=po_detail,
                                quantity_received=quantities[i],
                                condition=condition,
                                notes=f"Lot: {lot_numbers[i] if i < len(lot_numbers) else ''}"
                            )
                            
                            # Create inventory items if condition is good
                            if condition == GoodsReceiptDetail.Condition.GOOD:
                                lot_number = lot_numbers[i] if i < len(lot_numbers) else ''
                                expiry_date = expiry_dates[i] if i < len(expiry_dates) and expiry_dates[i] else None
                                
                                # Create individual inventory items
                                for _ in range(int(quantities[i])):
                                    InventoryItem.objects.create(
                                        product=po_detail.product,
                                        location=location,
                                        lot_number=lot_number,
                                        expiry_date=expiry_date,
                                        receipt_detail=receipt_detail,
                                        received_date=receipt_date,
                                        created_by=request.user
                                    )
                            
                            has_items_received = True
                    
                    # Update PO status based on receipt
                    if has_items_received:
                        # Check if all items are fully received
                        all_received = True
                        for detail in order.details.all():
                            if detail.received_quantity < detail.quantity:
                                all_received = False
                                break
                        
                        if all_received:
                            order.status = PurchaseOrder.Status.FULLY_RECEIVED
                        else:
                            order.status = PurchaseOrder.Status.PARTIALLY_RECEIVED
                        
                        order.save()
                    
                    messages.success(request, f'บันทึกการรับสินค้าตามใบสั่งซื้อ {order.po_number} เรียบร้อยแล้ว')
                    return redirect('purchase:receipt_detail', receipt_id=receipt.id)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    context = {
        'order': order,
        'details': details,
        'locations': locations,
        'today': timezone.now().date(),
        'now': timezone.now(),
        'conditions': GoodsReceiptDetail.Condition.choices
    }
    
    return render(request, 'purchase/receipt_form.html', context)

# ==============================================
# Reports Views
# ==============================================

@login_required
def purchase_reports(request):
    """หน้าแสดงรายงานสรุปการจัดซื้อ"""
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    selected_supplier = request.GET.get('supplier', '')
    
    # เริ่มต้นเป็นช่วงเวลา 30 วันล่าสุด ถ้าไม่ได้ระบุ
    if not start_date:
        start_date = (timezone.now() - timezone.timedelta(days=30))
    else:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # ข้อมูลพื้นฐานที่ใช้ในทุกรายงาน
    suppliers = Supplier.objects.filter(status=Supplier.Status.ACTIVE).order_by('company_name')
    
    # คิวรี่หลักสำหรับ PO และ PR
    orders = PurchaseOrder.objects.filter(
        order_date__range=[start_date, end_date]
    )
    
    requisitions = PurchaseRequisition.objects.filter(
        request_date__range=[start_date, end_date]
    )
    
    if selected_supplier:
        orders = orders.filter(supplier_id=selected_supplier)
    
    # สรุปข้อมูลหลัก
    total_orders = orders.count()
    total_amount = orders.aggregate(total=Sum('details__subtotal'))['total'] or 0
    total_requisitions = requisitions.count()
    
    # คำนวณข้อมูลสถิติ
    pending_orders = orders.filter(status=PurchaseOrder.Status.PENDING).count()
    completed_orders = orders.filter(status=PurchaseOrder.Status.FULLY_RECEIVED).count()
    pending_requisitions = requisitions.filter(status=PurchaseRequisition.Status.PENDING).count()
    
    avg_order_amount = total_amount / total_orders if total_orders > 0 else 0
    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
    
    # สรุปข้อมูลหลัก
    summary = {
        'total_orders': total_orders,
        'total_amount': total_amount,
        'total_requisitions': total_requisitions,
        'avg_order_amount': avg_order_amount,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'pending_requisitions': pending_requisitions,
        'completion_rate': completion_rate,
    }
    
    # สถิติแยกตามสถานะ
    status_breakdown = {
        'pr_draft': requisitions.filter(status=PurchaseRequisition.Status.DRAFT).count(),
        'pr_pending': requisitions.filter(status=PurchaseRequisition.Status.PENDING).count(),
        'pr_approved': requisitions.filter(status=PurchaseRequisition.Status.APPROVED).count(),
        'pr_rejected': requisitions.filter(
            status__in=[PurchaseRequisition.Status.REJECTED, PurchaseRequisition.Status.CANCELLED]
        ).count(),
        'po_draft': orders.filter(status=PurchaseOrder.Status.DRAFT).count(),
        'po_pending': orders.filter(status=PurchaseOrder.Status.PENDING).count(),
        'po_approved': orders.filter(status=PurchaseOrder.Status.APPROVED).count(),
        'po_received': orders.filter(status=PurchaseOrder.Status.FULLY_RECEIVED).count(),
    }
    
    # ข้อมูลแนวโน้มรายเดือน (ย้อนหลัง 6 เดือน)
    monthly_data = []
    for i in range(5, -1, -1):
        month_date = (timezone.now() - timezone.timedelta(days=30*i)).date()
        month_start = month_date.replace(day=1)
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timezone.timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timezone.timedelta(days=1)
        
        month_orders = PurchaseOrder.objects.filter(
            order_date__range=[month_start, month_end]
        )
        if selected_supplier:
            month_orders = month_orders.filter(supplier_id=selected_supplier)
        
        month_amount = month_orders.aggregate(total=Sum('details__subtotal'))['total'] or 0
        
        monthly_data.append({
            'month_name': month_date.strftime('%B %Y'),
            'total_amount': month_amount,
        })
    
    # สินค้าที่สั่งซื้อมากที่สุด
    top_products = Product.objects.annotate(
        order_count=Count('purchaseorderdetail', 
            filter=Q(
                purchaseorderdetail__purchase_order__order_date__range=[start_date, end_date],
                purchaseorderdetail__purchase_order__status__in=[
                    PurchaseOrder.Status.APPROVED,
                    PurchaseOrder.Status.PARTIALLY_RECEIVED,
                    PurchaseOrder.Status.FULLY_RECEIVED
                ]
            )
        ),
        total_quantity=Sum('purchaseorderdetail__quantity', 
            filter=Q(
                purchaseorderdetail__purchase_order__order_date__range=[start_date, end_date],
                purchaseorderdetail__purchase_order__status__in=[
                    PurchaseOrder.Status.APPROVED,
                    PurchaseOrder.Status.PARTIALLY_RECEIVED,
                    PurchaseOrder.Status.FULLY_RECEIVED
                ]
            )
        ),
        total_amount=Sum('purchaseorderdetail__subtotal', 
            filter=Q(
                purchaseorderdetail__purchase_order__order_date__range=[start_date, end_date],
                purchaseorderdetail__purchase_order__status__in=[
                    PurchaseOrder.Status.APPROVED,
                    PurchaseOrder.Status.PARTIALLY_RECEIVED,
                    PurchaseOrder.Status.FULLY_RECEIVED
                ]
            )
        )
    ).filter(order_count__gt=0).order_by('-order_count')[:5]
    
    # ผู้ขายยอดนิยม
    top_suppliers = Supplier.objects.annotate(
        order_count=Count('purchase_orders', 
            filter=Q(
                purchase_orders__order_date__range=[start_date, end_date],
                purchase_orders__status__in=[
                    PurchaseOrder.Status.APPROVED,
                    PurchaseOrder.Status.PARTIALLY_RECEIVED,
                    PurchaseOrder.Status.FULLY_RECEIVED
                ]
            )
        ),
        total_amount=Sum('purchase_orders__details__subtotal', 
            filter=Q(
                purchase_orders__order_date__range=[start_date, end_date],
                purchase_orders__status__in=[
                    PurchaseOrder.Status.APPROVED,
                    PurchaseOrder.Status.PARTIALLY_RECEIVED,
                    PurchaseOrder.Status.FULLY_RECEIVED
                ]
            )
        )
    ).filter(order_count__gt=0).order_by('-total_amount')[:5]
    
    # กิจกรรมล่าสุด
    recent_activities = []
    recent_pos = PurchaseOrder.objects.filter(
        order_date__range=[start_date, end_date]
    ).order_by('-created_at')[:5]
    
    for po in recent_pos:
        recent_activities.append({
            'description': f'สร้างใบสั่งซื้อ {po.po_number} จากผู้ขาย {po.supplier.company_name}',
            'timestamp': po.created_at,
        })
    
    recent_prs = PurchaseRequisition.objects.filter(
        request_date__range=[start_date, end_date]
    ).order_by('-created_at')[:3]
    
    for pr in recent_prs:
        recent_activities.append({
            'description': f'สร้างใบขอซื้อ {pr.pr_number} โดย {pr.requested_by.get_full_name()}',
            'timestamp': pr.created_at,
        })
    
    # เรียงตามเวลา
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:8]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'selected_supplier': selected_supplier,
        'suppliers': suppliers,
        'summary': summary,
        'status_breakdown': status_breakdown,
        'monthly_data': monthly_data,
        'top_products': top_products,
        'top_suppliers': top_suppliers,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'purchase/reports.html', context)

@login_required
def export_purchase_orders(request):
    """ส่งออกข้อมูลใบสั่งซื้อในรูปแบบ CSV"""
    import csv
    from django.http import HttpResponse
    
    # รับพารามิเตอร์สำหรับการกรอง
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')
    
    # สร้างคิวรี่สำหรับการดึงข้อมูล
    orders = PurchaseOrder.objects.all()
    
    # ใช้ตัวกรองหากมีการระบุ
    if date_from:
        orders = orders.filter(order_date__gte=date_from)
    if date_to:
        orders = orders.filter(order_date__lte=date_to)
    if status:
        orders = orders.filter(status=status)
    
    # เรียงลำดับตามวันที่
    orders = orders.order_by('-order_date')
    
    # สร้างการตอบสนองสำหรับการดาวน์โหลด
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchase_orders.csv"'
    
    # สร้างไฟล์ CSV
    writer = csv.writer(response)
    
    # เขียนหัวข้อคอลัมน์
    writer.writerow([
        'PO Number', 'Supplier', 'Order Date', 'Expected Delivery', 
        'Status', 'Total Value', 'Created By', 'PR Reference'
    ])
    
    # เขียนข้อมูล
    for order in orders:
        writer.writerow([
            order.po_number,
            order.supplier.company_name,
            order.order_date.strftime('%Y-%m-%d'),
            order.expected_delivery_date.strftime('%Y-%m-%d'),
            order.get_status_display(),
            order.total_amount,
            order.created_by.get_full_name(),
            order.purchase_requisition.pr_number if order.purchase_requisition else 'N/A'
        ])
    
    return response

@login_required
def export_purchase_requisitions(request):
    """ส่งออกข้อมูลใบขอซื้อในรูปแบบ CSV"""
    import csv
    from django.http import HttpResponse
    
    # รับพารามิเตอร์สำหรับการกรอง
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')
    
    # สร้างคิวรี่สำหรับการดึงข้อมูล
    requisitions = PurchaseRequisition.objects.all()
    
    # ใช้ตัวกรองหากมีการระบุ
    if date_from:
        requisitions = requisitions.filter(request_date__gte=date_from)
    if date_to:
        requisitions = requisitions.filter(request_date__lte=date_to)
    if status:
        requisitions = requisitions.filter(status=status)
    
    # เรียงลำดับตามวันที่
    requisitions = requisitions.order_by('-request_date')
    
    # สร้างการตอบสนองสำหรับการดาวน์โหลด
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchase_requisitions.csv"'
    
    # สร้างไฟล์ CSV
    writer = csv.writer(response)
    
    # เขียนหัวข้อคอลัมน์
    writer.writerow([
        'PR Number', 'Department', 'Requested By', 'Request Date', 
        'Required Date', 'Status', 'Total Items'
    ])
    
    # เขียนข้อมูล
    for req in requisitions:
        writer.writerow([
            req.pr_number,
            req.department,
            req.requested_by.get_full_name(),
            req.request_date.strftime('%Y-%m-%d'),
            req.required_date.strftime('%Y-%m-%d'),
            req.get_status_display(),
            req.details.count()
        ])
    
    return response

# ==============================================
# API Views
# ==============================================

@login_required
def get_product_prices(request, supplier_id):
    """API endpoint to get the most recent prices of products from a supplier"""
    try:
        supplier = get_object_or_404(Supplier, id=supplier_id)
        product_prices = {}
        
        # First check for prices in ProductSupplier model
        from App_Products.models import ProductSupplier
        supplier_products = ProductSupplier.objects.filter(supplier=supplier).select_related('product')
        
        for sp in supplier_products:
            product_prices[str(sp.product.id)] = {
                'unit_price': str(sp.unit_price),  # Convert Decimal to string to avoid JSON issues
                'product_name': sp.product.name,
                'product_code': sp.product.sku,  # Changed from code to sku
                'source': 'product_supplier',
                'min_qty': sp.minimum_order_quantity
            }
        
        # Then check purchase order history
        orders = PurchaseOrder.objects.filter(
            supplier=supplier,
            status__in=[
                PurchaseOrder.Status.APPROVED,
                PurchaseOrder.Status.PARTIALLY_RECEIVED,
                PurchaseOrder.Status.FULLY_RECEIVED
            ]
        ).select_related('supplier').prefetch_related('details__product').order_by('-order_date')
        
        for order in orders:
            for detail in order.details.all():
                product_id = str(detail.product.id)
                if product_id not in product_prices:
                    product_prices[product_id] = {
                        'unit_price': str(detail.unit_price),  # Convert Decimal to string to avoid JSON issues
                        'product_name': detail.product.name,
                        'product_code': detail.product.sku,  # Changed from code to sku
                        'source': 'purchase_order',
                        'order_date': order.order_date.strftime('%Y-%m-%d')
                    }
        
        return JsonResponse({
            'success': True, 
            'product_prices': product_prices,
            'supplier_name': supplier.company_name
        })
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        })
