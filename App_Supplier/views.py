from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, Max, Avg
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
import csv
from datetime import timedelta
from .models import Supplier, ContactHistory
from App_Purchase.models import PurchaseOrder

@login_required
def supplier_dashboard(request):
    """แสดงข้อมูลภาพรวมของซัพพลายเออร์"""
    # ข้อมูลจำนวนซัพพลายเออร์
    total_suppliers = Supplier.objects.count()
    active_suppliers = Supplier.objects.filter(status='active').count()
    inactive_suppliers = Supplier.objects.filter(status='inactive').count()
    manufacturer_count = Supplier.objects.filter(category='manufacturer').count()
    distributor_count = Supplier.objects.filter(category='distributor').count()
    service_count = Supplier.objects.filter(category='service').count()
    
    # ซัพพลายเออร์ที่มีการติดต่อล่าสุด
    recent_contacts = ContactHistory.objects.select_related('supplier').order_by('-contact_date')[:5]
    
    # ซัพพลายเออร์ล่าสุด
    recent_suppliers = Supplier.objects.order_by('-created_at')[:5]
    
    # กิจกรรมที่ต้องทำ (เช่น ซัพพลายเออร์ที่ไม่มีการติดต่อมากกว่า 60 วัน)
    two_months_ago = timezone.now() - timedelta(days=60)
    last_contact_dates = ContactHistory.objects.filter(
        supplier__status='active'
    ).values('supplier').annotate(
        latest_contact=Max('contact_date')
    )
    
    suppliers_need_contact = []
    for item in last_contact_dates:
        if item['latest_contact'] < two_months_ago:
            supplier = Supplier.objects.get(id=item['supplier'])
            suppliers_need_contact.append({
                'supplier': supplier,
                'last_contact': item['latest_contact'],
                'days_since_contact': (timezone.now().date() - item['latest_contact'].date()).days
            })
    
    # ซัพพลายเออร์ที่ไม่เคยมีการติดต่อเลย
    never_contacted_suppliers = Supplier.objects.filter(
        status='active'
    ).exclude(
        id__in=ContactHistory.objects.values_list('supplier_id', flat=True)
    )[:5]
    
    # ซัพพลายเออร์ที่มีการสั่งซื้อล่าสุด
    try:
        recent_orders = PurchaseOrder.objects.select_related('supplier').order_by('-created_at')[:5]
    except:
        recent_orders = []
    
    # ข้อมูลการติดต่อประจำเดือน
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_contacts = ContactHistory.objects.filter(
        contact_date__year=current_year,
        contact_date__month=current_month
    ).count()
    
    # ซัพพลายเออร์ที่มีการสั่งซื้อสูงสุด
    try:
        top_suppliers_by_orders = Supplier.objects.annotate(
            order_count=Count('purchase_orders')
        ).order_by('-order_count')[:5]
    except:
        top_suppliers_by_orders = []
    
    # แยกตามภูมิภาค
    suppliers_by_region = Supplier.objects.values('state').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
        
    context = {
        'page_title': 'ภาพรวมซัพพลายเออร์',
        'total_suppliers': total_suppliers,
        'active_suppliers': active_suppliers,
        'inactive_suppliers': inactive_suppliers,
        'manufacturer_count': manufacturer_count,
        'distributor_count': distributor_count,
        'service_count': service_count,
        'recent_contacts': recent_contacts,
        'recent_suppliers': recent_suppliers,
        'suppliers_need_contact': suppliers_need_contact[:5],  # แสดงเพียง 5 รายการ
        'never_contacted_suppliers': never_contacted_suppliers,
        'recent_orders': recent_orders,
        'monthly_contacts': monthly_contacts,
        'top_suppliers_by_orders': top_suppliers_by_orders,
        'suppliers_by_region': suppliers_by_region,
    }
    
    return render(request, 'suppliers/dashboard.html', context)

@login_required
def supplier_list(request):
    """แสดงรายการซัพพลายเออร์ทั้งหมด"""
    suppliers = Supplier.objects.all()
    
    # ข้อมูลภาพรวม
    total_suppliers = suppliers.count()
    active_suppliers = suppliers.filter(status='active').count()
    manufacturer_count = suppliers.filter(category='manufacturer').count()
    distributor_count = suppliers.filter(category='distributor').count()
    service_count = suppliers.filter(category='service').count()
    
    # การกรองข้อมูล
    category_filter = request.GET.get('category')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q')
    
    if category_filter:
        suppliers = suppliers.filter(category=category_filter)
    
    if status_filter:
        suppliers = suppliers.filter(status=status_filter)
    
    if search_query:
        suppliers = suppliers.filter(
            Q(company_name__icontains=search_query) |
            Q(contact_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(supplier_code__icontains=search_query)
        )
    
    context = {
        'suppliers': suppliers,
        'total_suppliers': total_suppliers,
        'active_suppliers': active_suppliers,
        'manufacturer_count': manufacturer_count,
        'distributor_count': distributor_count,
        'service_count': service_count,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'suppliers/supplier_list.html', context)

@login_required
def supplier_detail(request, supplier_id):
    """แสดงรายละเอียดซัพพลายเออร์"""
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    
    # ประวัติการติดต่อ
    contact_histories = supplier.contact_histories.all().order_by('-contact_date')
    
    context = {
        'supplier': supplier,
        'contact_histories': contact_histories,
    }
    
    return render(request, 'suppliers/supplier_detail.html', context)

@login_required
def supplier_add(request):
    """เพิ่มซัพพลายเออร์ใหม่"""
    if request.method == 'POST':
        # ดึงข้อมูลจากฟอร์ม
        company_name = request.POST.get('company_name')
        contact_name = request.POST.get('contact_name')
        contact_title = request.POST.get('contact_title', '')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        fax_number = request.POST.get('fax_number', '')
        website = request.POST.get('website', '')
        
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postal_code = request.POST.get('postal_code')
        country = request.POST.get('country', 'ไทย')
        
        bank_account_number = request.POST.get('bank_account_number', '')
        bank_name = request.POST.get('bank_name', '')
        payment_terms = request.POST.get('payment_terms', '')
        credit_limit = request.POST.get('credit_limit', 0)
        tax_id = request.POST.get('tax_id', '')
        
        category = request.POST.get('category')
        status = request.POST.get('status', 'active')
        
        try:
            supplier = Supplier.objects.create(
                company_name=company_name,
                contact_name=contact_name,
                contact_title=contact_title,
                email=email,
                phone_number=phone_number,
                fax_number=fax_number,
                website=website,
                address=address,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                bank_account_number=bank_account_number,
                bank_name=bank_name,
                payment_terms=payment_terms,
                credit_limit=credit_limit,
                tax_id=tax_id,
                category=category,
                status=status
            )
            messages.success(request, f'เพิ่มซัพพลายเออร์ {company_name} เรียบร้อยแล้ว')
            return redirect('suppliers:supplier_detail', supplier_id=supplier.id)
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    context = {
        'page_title': 'เพิ่มซัพพลายเออร์',
        'categories': Supplier.Category.choices,
        'statuses': Supplier.Status.choices,
    }
    
    return render(request, 'suppliers/supplier_add.html', context)

@login_required
def supplier_edit(request, supplier_id):
    """แก้ไขข้อมูลซัพพลายเออร์"""
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    
    if request.method == 'POST':
        # ดึงข้อมูลจากฟอร์ม
        supplier.company_name = request.POST.get('company_name')
        supplier.contact_name = request.POST.get('contact_name')
        supplier.contact_title = request.POST.get('contact_title', '')
        supplier.email = request.POST.get('email')
        supplier.phone_number = request.POST.get('phone_number')
        supplier.fax_number = request.POST.get('fax_number', '')
        supplier.website = request.POST.get('website', '')
        
        supplier.address = request.POST.get('address')
        supplier.city = request.POST.get('city')
        supplier.state = request.POST.get('state')
        supplier.postal_code = request.POST.get('postal_code')
        supplier.country = request.POST.get('country', 'ไทย')
        
        supplier.bank_account_number = request.POST.get('bank_account_number', '')
        supplier.bank_name = request.POST.get('bank_name', '')
        supplier.payment_terms = request.POST.get('payment_terms', '')
        supplier.credit_limit = request.POST.get('credit_limit', 0)
        supplier.tax_id = request.POST.get('tax_id', '')
        
        supplier.category = request.POST.get('category')
        supplier.status = request.POST.get('status', 'active')
        
        try:
            supplier.save()
            messages.success(request, f'อัปเดตข้อมูลซัพพลายเออร์ {supplier.company_name} เรียบร้อยแล้ว')
            return redirect('suppliers:supplier_detail', supplier_id=supplier.id)
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    context = {
        'supplier': supplier,
        'page_title': f'แก้ไขซัพพลายเออร์: {supplier.company_name}',
        'categories': Supplier.Category.choices,
        'statuses': Supplier.Status.choices,
    }
    
    return render(request, 'suppliers/supplier_edit.html', context)

@login_required
def add_contact_history(request, supplier_id):
    """เพิ่มประวัติการติดต่อให้กับซัพพลายเออร์"""
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    
    if request.method == 'POST':
        contact_type = request.POST.get('contact_type')
        notes = request.POST.get('notes')
        contact_date_str = request.POST.get('contact_date')
        
        # ถ้าไม่มีวันที่ ให้ใช้วันที่ปัจจุบัน
        if contact_date_str:
            try:
                # รองรับรูปแบบวันที่แบบ ISO (HTML datetime-local)
                if 'T' in contact_date_str:
                    contact_date = timezone.datetime.strptime(contact_date_str, '%Y-%m-%dT%H:%M')
                # รองรับรูปแบบวันที่แบบเดิม
                else:
                    contact_date = timezone.datetime.strptime(contact_date_str, '%Y-%m-%d %H:%M')
            except ValueError:
                # ถ้าแปลงไม่ได้ ให้ใช้วันที่ปัจจุบัน
                messages.warning(request, f'รูปแบบวันที่ไม่ถูกต้อง ระบบใช้วันที่ปัจจุบันแทน')
                contact_date = timezone.now()
        else:
            contact_date = timezone.now()
        
        try:
            contact = ContactHistory.objects.create(
                supplier=supplier,
                contact_type=contact_type,
                notes=notes,
                contact_date=contact_date,
                created_by=request.user
            )
            
            if request.headers.get('HX-Request'):
                # สำหรับการร้องขอแบบ HTMX
                return render(request, 'suppliers/partials/contact_history_item.html', {'contact': contact})
                
            messages.success(request, f'เพิ่มประวัติการติดต่อเรียบร้อยแล้ว')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return redirect('suppliers:supplier_detail', supplier_id=supplier.id)

@login_required
def delete_contact_history(request, supplier_id, contact_id):
    """ลบประวัติการติดต่อ"""
    contact = get_object_or_404(ContactHistory, pk=contact_id, supplier_id=supplier_id)
    
    if request.method == 'POST':
        try:
            contact.delete()
            messages.success(request, 'ลบประวัติการติดต่อเรียบร้อยแล้ว')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return redirect('suppliers:supplier_detail', supplier_id=supplier_id)

@login_required
def supplier_reports(request):
    """แสดงรายงานและการวิเคราะห์ข้อมูลซัพพลายเออร์"""
    # จำนวนซัพพลายเออร์ตามประเภท
    supplier_by_category = Supplier.objects.values('category').annotate(count=Count('id'))
    category_data = {item['category']: item['count'] for item in supplier_by_category}
    
    # จำนวนซัพพลายเออร์ตามสถานะ
    supplier_by_status = Supplier.objects.values('status').annotate(count=Count('id'))
    status_data = {item['status']: item['count'] for item in supplier_by_status}
    
    # จำนวนซัพพลายเออร์ตามภูมิภาค/จังหวัด
    supplier_by_state = Supplier.objects.values('state').annotate(count=Count('id')).order_by('-count')[:10]
    
    # การติดต่อแยกตามประเภท
    contact_by_type = ContactHistory.objects.values('contact_type').annotate(count=Count('id'))
    contact_type_data = {item['contact_type']: item['count'] for item in contact_by_type}
    
    # จำนวนการติดต่อเฉลี่ยต่อซัพพลายเออร์
    try:
        total_contacts = ContactHistory.objects.count()
        suppliers_with_contact = ContactHistory.objects.values('supplier').distinct().count()
        avg_contacts_per_supplier = total_contacts / suppliers_with_contact if suppliers_with_contact > 0 else 0
    except:
        avg_contacts_per_supplier = 0
    
    # ซัพพลายเออร์ที่มีการติดต่อมากที่สุด 10 อันดับแรก
    top_contacted_suppliers = Supplier.objects.annotate(
        contact_count=Count('contact_histories')
    ).order_by('-contact_count')[:10]
    
    # ประวัติการติดต่อรายเดือน
    # สร้างข้อมูลการติดต่อตามเดือนในช่วง 12 เดือนที่ผ่านมา
    now = timezone.now()
    month_data = []
    
    for i in range(11, -1, -1):
        month_date = now - timedelta(days=30*i)
        month_name = month_date.strftime('%B %Y')
        month_contacts = ContactHistory.objects.filter(
            contact_date__year=month_date.year,
            contact_date__month=month_date.month
        ).count()
        month_data.append({
            'month': month_name,
            'count': month_contacts
        })
    
    try:
        # ซัพพลายเออร์ที่มีการสั่งซื้อมากที่สุด 10 อันดับแรก
        top_ordered_suppliers = Supplier.objects.annotate(
            order_count=Count('purchase_orders')
        ).order_by('-order_count')[:10]
        
        # ซัพพลายเออร์ที่มีมูลค่าการสั่งซื้อมากที่สุด
        try:
            top_value_suppliers = Supplier.objects.annotate(
                total_value=Sum('purchase_orders__total_amount')
            ).order_by('-total_value')[:10]
        except:
            top_value_suppliers = []
            
        # ข้อมูลรายเดือนของคำสั่งซื้อจากซัพพลายเออร์
        month_orders = []
        for i in range(11, -1, -1):
            month_date = now - timedelta(days=30*i)
            month_name = month_date.strftime('%B %Y')
            try:
                month_order_count = PurchaseOrder.objects.filter(
                    created_at__year=month_date.year,
                    created_at__month=month_date.month
                ).count()
            except:
                month_order_count = 0
            month_orders.append({
                'month': month_name,
                'count': month_order_count
            })
    except:
        top_ordered_suppliers = []
        top_value_suppliers = []
        month_orders = []
    
    # ซัพพลายเออร์ที่ไม่มีการติดต่อในช่วง 3 เดือนที่ผ่านมา
    three_months_ago = now - timedelta(days=90)
    inactive_suppliers = Supplier.objects.filter(status='active').exclude(
        id__in=ContactHistory.objects.filter(
            contact_date__gte=three_months_ago
        ).values_list('supplier_id', flat=True)
    )
    
    context = {
        'page_title': 'รายงานซัพพลายเออร์',
        'category_data': category_data,
        'status_data': status_data,
        'supplier_by_state': supplier_by_state,
        'contact_type_data': contact_type_data,
        'avg_contacts_per_supplier': round(avg_contacts_per_supplier, 2),
        'top_contacted_suppliers': top_contacted_suppliers,
        'top_ordered_suppliers': top_ordered_suppliers,
        'top_value_suppliers': top_value_suppliers,
        'month_data': month_data,
        'month_orders': month_orders,
        'inactive_suppliers': inactive_suppliers,
    }
    
    return render(request, 'suppliers/supplier_reports.html', context)

@login_required
def export_suppliers(request):
    """ส่งออกข้อมูลซัพพลายเออร์ในรูปแบบ CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="suppliers_export_{}.csv"'.format(
        timezone.now().strftime('%Y%m%d_%H%M%S')
    )
    
    # ฟิลเตอร์
    category = request.GET.get('category')
    status = request.GET.get('status')
    
    suppliers = Supplier.objects.all()
    
    if category:
        suppliers = suppliers.filter(category=category)
    
    if status:
        suppliers = suppliers.filter(status=status)
    
    writer = csv.writer(response)
    writer.writerow([
        'รหัสซัพพลายเออร์', 
        'ชื่อบริษัท', 
        'ผู้ติดต่อ', 
        'ตำแหน่ง', 
        'อีเมล', 
        'เบอร์โทรศัพท์', 
        'เบอร์แฟกซ์',
        'เว็บไซต์',
        'ที่อยู่', 
        'เมือง',
        'จังหวัด', 
        'รหัสไปรษณีย์', 
        'ประเทศ',
        'เลขประจำตัวผู้เสียภาษี', 
        'ธนาคาร',
        'เลขบัญชี',
        'เงื่อนไขการชำระเงิน',
        'วงเงินเครดิต',
        'ประเภท', 
        'สถานะ',
        'วันที่สร้าง',
        'วันที่แก้ไขล่าสุด',
        'จำนวนครั้งที่ติดต่อ',
        'วันที่ติดต่อล่าสุด'
    ])
    
    for supplier in suppliers:
        # หาข้อมูลประวัติการติดต่อ
        contact_count = ContactHistory.objects.filter(supplier=supplier).count()
        try:
            latest_contact = ContactHistory.objects.filter(supplier=supplier).latest('contact_date')
            latest_contact_date = latest_contact.contact_date.strftime('%Y-%m-%d')
        except:
            latest_contact_date = 'ไม่มีข้อมูล'
        
        writer.writerow([
            supplier.supplier_code or '',
            supplier.company_name,
            supplier.contact_name,
            supplier.contact_title,
            supplier.email,
            supplier.phone_number,
            supplier.fax_number or '',
            supplier.website or '',
            supplier.address,
            supplier.city,
            supplier.state,
            supplier.postal_code,
            supplier.country,
            supplier.tax_id or '',
            supplier.bank_name or '',
            supplier.bank_account_number or '',
            supplier.payment_terms or '',
            supplier.credit_limit,
            supplier.get_category_display(),
            supplier.get_status_display(),
            supplier.created_at.strftime('%Y-%m-%d'),
            supplier.updated_at.strftime('%Y-%m-%d'),
            contact_count,
            latest_contact_date
        ])
    
    return response
