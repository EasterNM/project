from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Sum, F, Q
from .models import OrderRequest, OrderDetail, PickingOrder, PickingDetail, Invoice
from App_Customer.models import Customer
from App_Products.models import Product
from App_Inventory.models import InventoryItem

@login_required
def order_dashboard(request):
    """แสดงหน้า Dashboard หลักของระบบการสั่งซื้อสินค้า"""
    # ข้อมูลภาพรวมออเดอร์
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    
    # จำนวนออเดอร์แยกตามสถานะ
    order_stats = OrderRequest.objects.values('status').annotate(count=Count('order_id'))
    order_stats_dict = {item['status']: item['count'] for item in order_stats}
    
    # ออเดอร์ที่รอดำเนินการ
    pending_orders = OrderRequest.objects.filter(status=OrderRequest.Status.PENDING).order_by('-created_at')[:5]
    
    # ออเดอร์ที่กำลังดำเนินการ
    processing_orders = OrderRequest.objects.filter(status=OrderRequest.Status.PROCESSING).order_by('-created_at')[:5]
    
    # ออเดอร์ที่สร้างในเดือนนี้
    monthly_orders = OrderRequest.objects.filter(created_at__gte=this_month_start).count()
    
    # มูลค่าการขายในเดือนนี้
    monthly_sales = Invoice.objects.filter(issue_date__gte=this_month_start).aggregate(total=Sum('grand_total'))['total'] or 0
    
    # ออเดอร์ล่าสุด
    recent_orders = OrderRequest.objects.select_related('customer').order_by('-created_at')[:10]
    
    context = {
        'page_title': 'ระบบการสั่งซื้อสินค้า',
        'pending_count': order_stats_dict.get(OrderRequest.Status.PENDING, 0),
        'processing_count': order_stats_dict.get(OrderRequest.Status.PROCESSING, 0),
        'completed_count': order_stats_dict.get(OrderRequest.Status.COMPLETED, 0),
        'cancelled_count': order_stats_dict.get(OrderRequest.Status.CANCELLED, 0),
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'monthly_orders': monthly_orders,
        'monthly_sales': monthly_sales,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'orders/dashboard.html', context)

@login_required
def create_order(request):
    """หน้าสร้างออเดอร์ใหม่"""
    customers = Customer.objects.all()
    products = Product.objects.all()
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        note = request.POST.get('note', '')
        
        if not customer_id or not product_ids:
            messages.error(request, 'กรุณาระบุข้อมูลให้ครบถ้วน')
            return redirect('orders:create_order')
        
        try:
            customer = Customer.objects.get(id=customer_id)
            
            with transaction.atomic():
                # สร้างออเดอร์ใหม่
                order = OrderRequest.objects.create(
                    customer=customer,
                    created_by=request.user,
                    note=note
                )
                
                # เพิ่มรายการสินค้า
                for i, product_id in enumerate(product_ids):
                    if not product_id:
                        continue
                    
                    quantity = int(quantities[i]) if quantities[i] else 1
                    product = Product.objects.get(id=product_id)
                    
                    OrderDetail.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity
                    )
                
                # สร้าง PickingOrder อัตโนมัติ
                PickingOrder.objects.create(
                    order_request=order
                )
                
                messages.success(request, f'สร้างออเดอร์ {order.order_id} เรียบร้อยแล้ว')
                return redirect('orders:order_detail', order_id=order.order_id)
                
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            return redirect('orders:create_order')
    
    context = {
        'page_title': 'สร้างออเดอร์ใหม่',
        'customers': customers,
        'products': products,
    }
    
    return render(request, 'orders/create_order.html', context)

@login_required
def order_list(request):
    """แสดงรายการออเดอร์ทั้งหมด"""
    status_filter = request.GET.get('status', '')
    
    orders = OrderRequest.objects.all().order_by('-created_at')
    
    if status_filter and status_filter != 'ALL':
        orders = orders.filter(status=status_filter)
    
    context = {
        'page_title': 'รายการออเดอร์',
        'orders': orders,
        'status_filter': status_filter,
        'status_choices': OrderRequest.Status.choices,
    }
    
    return render(request, 'orders/order_list.html', context)

@login_required
def order_detail(request, order_id):
    """แสดงรายละเอียดของออเดอร์"""
    order = get_object_or_404(OrderRequest, order_id=order_id)
    order_details = order.details.all()
    
    # ตรวจสอบว่ามี PickingOrder หรือยัง
    try:
        picking_order = order.picking_order
        picking_details = picking_order.details.all()
    except PickingOrder.DoesNotExist:
        picking_order = None
        picking_details = []
    
    # ตรวจสอบว่ามี Invoice หรือยัง
    try:
        invoice = order.invoice
    except Invoice.DoesNotExist:
        invoice = None
    
    context = {
        'page_title': f'ออเดอร์ {order_id}',
        'order': order,
        'order_details': order_details,
        'picking_order': picking_order,
        'picking_details': picking_details,
        'invoice': invoice,
    }
    
    return render(request, 'orders/order_detail.html', context)

@login_required
def order_picking(request, order_id):
    """จัดการหน้าจัดสินค้าตามออเดอร์"""
    order = get_object_or_404(OrderRequest, order_id=order_id)
    
    try:
        picking_order = order.picking_order
    except PickingOrder.DoesNotExist:
        # สร้าง PickingOrder อัตโนมัติถ้ายังไม่มี
        picking_order = PickingOrder.objects.create(
            order_request=order
        )
    
    # ตรวจสอบว่ามี PickingDetail สำหรับทุก OrderDetail หรือยัง
    order_details = order.details.all()
    for order_detail in order_details:
        PickingDetail.objects.get_or_create(
            picking_order=picking_order,
            order_detail=order_detail
        )
    
    picking_details = picking_order.details.all()
    
    # จัดการกับการ POST request เมื่อทำการจัดสินค้า
    if request.method == 'POST':
        if 'update_status' in request.POST:
            new_status = request.POST.get('status')
            if new_status in [s[0] for s in PickingOrder.Status.choices]:
                picking_order.status = new_status
                
                # ถ้าจัดเสร็จแล้ว ให้อัพเดทสถานะของ Order ด้วย
                if new_status == PickingOrder.Status.COMPLETED:
                    # อัพเดทสถานะของ Order
                    order.status = OrderRequest.Status.PROCESSING
                    order.save()
                    
                    # อัพเดทสถานะของสินค้าในคลังเป็น "ขายแล้ว"
                    for detail in picking_order.details.all():
                        for item in detail.picked_items.all():
                            item.status = 'sold'  # เปลี่ยนสถานะเป็น "ขายแล้ว"
                            item.save()
                
                # ถ้าผู้จัดยังไม่ถูกกำหนด ให้กำหนดเป็นผู้ใช้ปัจจุบัน
                if not picking_order.picker and new_status != PickingOrder.Status.PENDING:
                    picking_order.picker = request.user
                
                picking_order.save()
                messages.success(request, f'อัพเดทสถานะการจัดสินค้าเป็น {picking_order.get_status_display()} เรียบร้อยแล้ว')
        
        elif 'picking_item' in request.POST:
            detail_id = request.POST.get('detail_id')
            serial_numbers = request.POST.getlist('serial_numbers')
            
            try:
                picking_detail = PickingDetail.objects.get(id=detail_id)
                
                # ลบรายการเก่าและเพิ่มรายการใหม่
                # ก่อนลบรายการเก่า ต้องคืนค่าสถานะสินค้ากลับเป็น "พร้อมใช้งาน"
                for old_item in picking_detail.picked_items.all():
                    old_item.status = 'available'  # คืนค่าสถานะเป็น "พร้อมใช้งาน"
                    old_item.save()
                    
                picking_detail.picked_items.clear()
                
                for sn in serial_numbers:
                    if sn.strip():
                        try:
                            item = InventoryItem.objects.get(serial_number=sn.strip())
                            # ตรวจสอบว่าสินค้ายังพร้อมใช้งานอยู่หรือไม่
                            if item.status != 'available':
                                messages.error(request, f'สินค้า Serial Number: {sn} มีสถานะเป็น {item.get_status_display()} ไม่สามารถเลือกได้')
                                continue
                                
                            # เพิ่มสินค้าและอัพเดทสถานะเป็น "จองแล้ว"
                            picking_detail.picked_items.add(item)
                            item.status = 'reserved'  # เปลี่ยนสถานะเป็น "จองแล้ว"
                            item.save()
                        except InventoryItem.DoesNotExist:
                            messages.error(request, f'ไม่พบ Serial Number: {sn}')
                
                messages.success(request, 'บันทึกรายการจัดสินค้าเรียบร้อยแล้ว')
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    # ดึงข้อมูลสินค้าคงเหลือสำหรับแสดงในหน้าจัดสินค้า
    inventory_items = {}
    for detail in picking_details:
        product_id = detail.order_detail.product.id
        inventory_items[product_id] = InventoryItem.objects.filter(
            product=detail.order_detail.product,
            status='available'
        )
    
    context = {
        'page_title': f'จัดสินค้าตามออเดอร์ {order_id}',
        'order': order,
        'picking_order': picking_order,
        'picking_details': picking_details,
        'inventory_items': inventory_items,
    }
    
    return render(request, 'orders/order_picking.html', context)

@login_required
def create_invoice(request, order_id):
    """สร้างใบแจ้งหนี้/ใบกำกับภาษีจากออเดอร์"""
    order = get_object_or_404(OrderRequest, order_id=order_id)
    
    # ตรวจสอบว่าออเดอร์อยู่ในสถานะที่สามารถสร้างใบแจ้งหนี้ได้หรือไม่
    if order.status not in [OrderRequest.Status.PROCESSING, OrderRequest.Status.COMPLETED]:
        messages.error(request, 'ไม่สามารถสร้างใบแจ้งหนี้ได้ เนื่องจากออเดอร์ยังไม่ได้ดำเนินการ')
        return redirect('orders:order_detail', order_id=order_id)
    
    # ตรวจสอบว่ามีใบแจ้งหนี้แล้วหรือยัง
    try:
        invoice = order.invoice
        messages.info(request, f'ออเดอร์นี้มีใบแจ้งหนี้แล้ว: {invoice.invoice_number}')
        return redirect('orders:invoice_detail', invoice_number=invoice.invoice_number)
    except Invoice.DoesNotExist:
        pass
    
    if request.method == 'POST':
        invoice_type = request.POST.get('invoice_type')
        discount_amount = request.POST.get('discount_amount', '0')
        vat_rate = request.POST.get('vat_rate', '7.00')
        due_date = request.POST.get('due_date')
        
        try:
            # สร้างใบแจ้งหนี้
            from decimal import Decimal
            invoice = Invoice.objects.create(
                order_request=order,
                invoice_type=invoice_type,
                created_by=request.user,
                discount_amount=Decimal(discount_amount),
                vat_rate=Decimal(vat_rate),
                due_date=due_date,
            )
            
            # อัพเดทสถานะออเดอร์เป็นเสร็จสิ้น
            order.status = OrderRequest.Status.COMPLETED
            order.save()
            
            # อัพเดทสถานะของสินค้าในคลังเป็น "ขายแล้ว" ถ้ายังไม่ได้อัพเดท
            try:
                # ดึง picking order สำหรับออเดอร์นี้
                picking_order = order.picking_order
                
                # วนลูปผ่านทุก picking detail
                for detail in picking_order.details.all():
                    for item in detail.picked_items.all():
                        if item.status != 'sold':  # อัพเดทเฉพาะรายการที่ยังไม่ได้อัพเดท
                            item.status = 'sold'  # เปลี่ยนสถานะเป็น "ขายแล้ว"
                            item.save()
            except Exception as e:
                # บันทึก log แต่ไม่หยุดการทำงาน
                print(f"Error updating inventory items: {str(e)}")
            
            messages.success(request, f'สร้างใบแจ้งหนี้ {invoice.invoice_number} เรียบร้อยแล้ว')
            return redirect('orders:invoice_detail', invoice_number=invoice.invoice_number)
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    # กำหนดวันที่ครบกำหนดชำระเป็น 30 วันจากวันที่ปัจจุบัน
    due_date = (timezone.now() + timezone.timedelta(days=30)).date()
    
    # ดึงรายละเอียดออเดอร์พร้อมผลรวมยอดเงิน
    from django.db.models import Sum
    order_details = order.details.all()
    total = order_details.aggregate(total=Sum('subtotal'))['total'] or 0
    
    context = {
        'page_title': f'สร้างใบแจ้งหนี้สำหรับออเดอร์ {order_id}',
        'order': order,
        'order_details': order_details,
        'order_total': total,
        'invoice_types': Invoice.InvoiceType.choices,
        'due_date': due_date,
    }
    
    return render(request, 'orders/create_invoice.html', context)

@login_required
def invoice_detail(request, invoice_number):
    """แสดงรายละเอียดใบแจ้งหนี้"""
    invoice = get_object_or_404(Invoice, invoice_number=invoice_number)
    order = invoice.order_request
    order_details = order.details.all()
    
    context = {
        'page_title': f'ใบแจ้งหนี้ {invoice_number}',
        'invoice': invoice,
        'order': order,
        'order_details': order_details,
    }
    
    return render(request, 'orders/invoice_detail.html', context)

@login_required  
def order_reports(request):
    """หน้าแสดงรายงานและการวิเคราะห์ออเดอร์"""
    from datetime import timedelta
    from django.db.models import Avg, Q
    from django.db.models.functions import TruncMonth
    
    # กำหนดช่วงเวลาการค้นหา
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    selected_customer = request.GET.get('customer', '')
    
    # เริ่มต้นเป็นช่วงเวลา 30 วันล่าสุด ถ้าไม่ได้ระบุ
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        from datetime import datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        from datetime import datetime
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # ข้อมูลพื้นฐาน
    customers = Customer.objects.all().order_by('name')
    
    # คิวรี่หลักสำหรับออเดอร์
    orders = OrderRequest.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    if selected_customer:
        orders = orders.filter(customer_id=selected_customer)
    
    # สรุปข้อมูลหลัก
    total_orders = orders.count()
    pending_orders = orders.filter(status=OrderRequest.Status.PENDING).count()
    processing_orders = orders.filter(status=OrderRequest.Status.PROCESSING).count()
    completed_orders = orders.filter(status=OrderRequest.Status.COMPLETED).count()
    cancelled_orders = orders.filter(status=OrderRequest.Status.CANCELLED).count()
    
    # มูลค่าการขาย
    invoices = Invoice.objects.filter(
        issue_date__range=[start_date, end_date]
    )
    if selected_customer:
        invoices = invoices.filter(order_request__customer_id=selected_customer)
    
    total_sales = invoices.aggregate(total=Sum('grand_total'))['total'] or 0
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
    
    # สถิติแยกตามสถานะ
    status_breakdown = {
        'pending': pending_orders,
        'processing': processing_orders,
        'completed': completed_orders,
        'cancelled': cancelled_orders,
    }
    
    # ข้อมูลแนวโน้มรายเดือน (ย้อนหลัง 6 เดือน)
    monthly_data = []
    for i in range(5, -1, -1):
        month_date = (timezone.now() - timedelta(days=30*i)).date()
        month_start = month_date.replace(day=1)
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
        
        month_orders = OrderRequest.objects.filter(
            created_at__date__range=[month_start, month_end]
        )
        if selected_customer:
            month_orders = month_orders.filter(customer_id=selected_customer)
        
        month_sales = Invoice.objects.filter(
            issue_date__range=[month_start, month_end]
        )
        if selected_customer:
            month_sales = month_sales.filter(order_request__customer_id=selected_customer)
        
        month_sales_amount = month_sales.aggregate(total=Sum('grand_total'))['total'] or 0
        
        monthly_data.append({
            'month_name': month_date.strftime('%B %Y'),
            'total_orders': month_orders.count(),
            'total_sales': month_sales_amount,
        })
    
    # สินค้าที่ขายดีที่สุด
    top_products = Product.objects.annotate(
        order_count=Count('order_details', 
            filter=Q(
                order_details__order__created_at__date__range=[start_date, end_date],
                order_details__order__status=OrderRequest.Status.COMPLETED
            )
        ),
        total_quantity=Sum('order_details__quantity', 
            filter=Q(
                order_details__order__created_at__date__range=[start_date, end_date],
                order_details__order__status=OrderRequest.Status.COMPLETED
            )
        ),
        total_sales=Sum('order_details__subtotal', 
            filter=Q(
                order_details__order__created_at__date__range=[start_date, end_date],
                order_details__order__status=OrderRequest.Status.COMPLETED
            )
        )
    ).filter(order_count__gt=0).order_by('-order_count')[:5]
    
    # ลูกค้าที่ซื้อมากที่สุด
    top_customers = Customer.objects.annotate(
        order_count=Count('orderrequest', 
            filter=Q(
                orderrequest__created_at__date__range=[start_date, end_date],
                orderrequest__status=OrderRequest.Status.COMPLETED
            )
        ),
        total_sales=Sum('orderrequest__invoice__grand_total', 
            filter=Q(
                orderrequest__created_at__date__range=[start_date, end_date],
                orderrequest__status=OrderRequest.Status.COMPLETED
            )
        )
    ).filter(order_count__gt=0).order_by('-total_sales')[:5]
    
    # กิจกรรมล่าสุด
    recent_activities = []
    
    recent_orders = OrderRequest.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).order_by('-created_at')[:5]
    
    for order in recent_orders:
        recent_activities.append({
            'description': f'สร้างออเดอร์ {order.order_id} จากลูกค้า {order.customer.name}',
            'timestamp': order.created_at,
        })
    
    recent_invoices = Invoice.objects.filter(
        issue_date__range=[start_date, end_date]
    ).order_by('-created_at')[:3]
    
    for invoice in recent_invoices:
        recent_activities.append({
            'description': f'สร้างใบแจ้งหนี้ {invoice.invoice_number} มูลค่า {invoice.grand_total:,.2f} บาท',
            'timestamp': invoice.created_at,
        })
    
    # เรียงตามเวลา
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:8]
    
    # สรุปข้อมูลหลัก
    summary = {
        'total_orders': total_orders,
        'total_sales': total_sales,
        'avg_order_value': avg_order_value,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'completion_rate': completion_rate,
    }
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'selected_customer': selected_customer,
        'customers': customers,
        'summary': summary,
        'status_breakdown': status_breakdown,
        'monthly_data': monthly_data,
        'top_products': top_products,
        'top_customers': top_customers,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'orders/reports.html', context)

@login_required
def export_orders(request):
    """ส่งออกข้อมูลออเดอร์ในรูปแบบ CSV"""
    import csv
    from django.http import HttpResponse
    
    # ดึงข้อมูลออเดอร์
    orders = OrderRequest.objects.all().order_by('-created_at')
    
    # กรองตามพารามิเตอร์ที่ได้รับ
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])
    
    # สร้างไฟล์ CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
    
    # เพิ่ม BOM สำหรับ UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow([
        'เลขที่ออเดอร์',
        'ลูกค้า',
        'สถานะ',
        'วันที่สร้าง',
        'สร้างโดย',
        'จำนวนรายการ',
        'หมายเหตุ'
    ])
    
    for order in orders:
        writer.writerow([
            order.order_id,
            order.customer.name,
            order.get_status_display(),
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.created_by.get_full_name() or order.created_by.username,
            order.details.count(),
            order.note or '-'
        ])
    
    return response

@login_required
def export_invoices(request):
    """ส่งออกข้อมูลใบแจ้งหนี้ในรูปแบบ CSV"""
    import csv
    from django.http import HttpResponse
    
    # ดึงข้อมูลใบแจ้งหนี้
    invoices = Invoice.objects.all().order_by('-created_at')
    
    # กรองตามพารามิเตอร์ที่ได้รับ
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        invoices = invoices.filter(issue_date__range=[start_date, end_date])
    
    # สร้างไฟล์ CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="invoices_export.csv"'
    
    # เพิ่ม BOM สำหรับ UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow([
        'เลขที่ใบแจ้งหนี้',
        'เลขที่ออเดอร์',
        'ลูกค้า',
        'ประเภทใบแจ้งหนี้',
        'วันที่ออกใบแจ้งหนี้',
        'วันที่ครบกำหนด',
        'ยอดรวมก่อนส่วนลด',
        'ส่วนลด',
        'ยอดหลังหักส่วนลด',
        'ภาษี',
        'ยอดรวมสุทธิ'
    ])
    
    for invoice in invoices:
        writer.writerow([
            invoice.invoice_number,
            invoice.order_request.order_id,
            invoice.order_request.customer.name,
            invoice.get_invoice_type_display(),
            invoice.issue_date.strftime('%Y-%m-%d'),
            invoice.due_date.strftime('%Y-%m-%d'),
            f'{invoice.total_amount:.2f}',
            f'{invoice.discount_amount:.2f}',
            f'{invoice.subtotal:.2f}',
            f'{invoice.vat_amount:.2f}',
            f'{invoice.grand_total:.2f}'
        ])
    
    return response
