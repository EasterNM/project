from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, Max, Avg, DateTimeField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import timedelta
import csv
from .models import Customer, CustomerContactHistory


@login_required
def customer_dashboard(request):
    """แสดงข้อมูลภาพรวมของลูกค้า"""
    # ข้อมูลจำนวนลูกค้า
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(status='active').count()
    inactive_customers = Customer.objects.filter(status='inactive').count()
    suspended_customers = Customer.objects.filter(status='suspended').count()
    individual_count = Customer.objects.filter(customer_type='individual').count()
    company_count = Customer.objects.filter(customer_type='company').count()
    
    # จำนวนลูกค้าตามระดับราคา
    price_a_count = Customer.objects.filter(price_tier='A').count()
    price_aa_count = Customer.objects.filter(price_tier='AA').count()
    price_aaa_count = Customer.objects.filter(price_tier='AAA').count()

    # ลูกค้าที่มีการติดต่อล่าสุด
    recent_contacts = CustomerContactHistory.objects.select_related('customer').order_by('-contact_date')[:5]
    
    # ลูกค้าล่าสุด
    recent_customers = Customer.objects.order_by('-created_at')[:5]
    
    # กิจกรรมที่ต้องทำ (เช่น ลูกค้าที่ไม่มีการติดต่อมากกว่า 60 วัน)
    two_months_ago = timezone.now() - timedelta(days=60)
    last_contact_dates = CustomerContactHistory.objects.filter(
        customer__status='active'
    ).values('customer').annotate(
        latest_contact=Max('contact_date')
    )
    
    customers_need_contact = []
    for item in last_contact_dates:
        if item['latest_contact'] < two_months_ago:
            customer = Customer.objects.get(id=item['customer'])
            customers_need_contact.append({
                'customer': customer,
                'days_since_contact': (timezone.now() - item['latest_contact']).days
            })
    
    # ลูกค้าที่ไม่เคยมีการติดต่อเลย
    never_contacted_customers = Customer.objects.filter(
        status='active'
    ).exclude(
        id__in=CustomerContactHistory.objects.values_list('customer_id', flat=True)
    )[:10]
    
    # ออเดอร์ล่าสุด (ถ้ามี)
    try:
        from App_OrderingProductForSale.models import OrderRequest
        recent_orders = OrderRequest.objects.select_related('customer').prefetch_related('details').order_by('-created_at')[:5]
    except ImportError:
        recent_orders = []
    
    # การติดต่อรายเดือน (ช่วง 6 เดือนที่ผ่านมา)
    now = timezone.now()
    monthly_contacts = []
    for i in range(5, -1, -1):  # 6 เดือนล่าสุด
        month_date = now - timedelta(days=30*i)
        month_contacts = CustomerContactHistory.objects.filter(
            contact_date__year=month_date.year,
            contact_date__month=month_date.month
        ).count()
        monthly_contacts.append({
            'month': month_date.strftime('%b %Y'),
            'count': month_contacts
        })
    
    # ลูกค้าตามจังหวัด 
    customers_by_region = Customer.objects.values('state').annotate(
        count=Count('id')
    ).exclude(state__isnull=True).exclude(state='').order_by('-count')[:10]
    
    # ข้อมูลเครดิต
    total_credit_limit = Customer.objects.aggregate(
        total=Sum('credit_limit')
    )['total'] or 0
    
    # ลูกค้าที่มีออเดอร์มากที่สุด (ถ้ามี)
    try:
        top_customers_by_orders = Customer.objects.annotate(
            order_count=Count('orderrequest')
        ).order_by('-order_count')[:5]
    except:
        top_customers_by_orders = []
    
    context = {
        'page_title': 'ภาพรวมลูกค้า',
        'total_customers': total_customers,
        'active_customers': active_customers,
        'inactive_customers': inactive_customers,
        'suspended_customers': suspended_customers,
        'individual_count': individual_count,
        'company_count': company_count,
        'price_a_count': price_a_count,
        'price_aa_count': price_aa_count,
        'price_aaa_count': price_aaa_count,
        'recent_contacts': recent_contacts,
        'recent_customers': recent_customers,
        'customers_need_contact': customers_need_contact[:5],  # แสดงเพียง 5 รายการ
        'never_contacted_customers': never_contacted_customers,
        'recent_orders': recent_orders,
        'monthly_contacts': monthly_contacts,
        'customers_by_region': customers_by_region,
        'total_credit_limit': total_credit_limit,
        'top_customers_by_orders': top_customers_by_orders,
    }
    
    return render(request, 'customers/enhanced_dashboard.html', context)


@login_required
def customer_list(request):
    """แสดงหน้ารายการลูกค้าทั้งหมด"""
    customers = Customer.objects.all()
    
    # ข้อมูลภาพรวม
    total_customers = customers.count()
    active_customers = customers.filter(status='active').count()
    individual_customers = customers.filter(customer_type='individual').count()
    company_customers = customers.filter(customer_type='company').count()
    price_a_customers = customers.filter(price_tier='A').count()
    price_aa_customers = customers.filter(price_tier='AA').count()
    price_aaa_customers = customers.filter(price_tier='AAA').count()
    
    # การกรองข้อมูล
    status_filter = request.GET.get('status')
    customer_type_filter = request.GET.get('customer_type')
    price_tier_filter = request.GET.get('price_tier')
    search_query = request.GET.get('q')
    
    if status_filter:
        customers = customers.filter(status=status_filter)
    
    if customer_type_filter:
        customers = customers.filter(customer_type=customer_type_filter)
        
    if price_tier_filter:
        customers = customers.filter(price_tier=price_tier_filter)
    
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(customer_code__icontains=search_query) |
            Q(contact_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    context = {
        'customers': customers,
        'total_customers': total_customers,
        'active_customers': active_customers,
        'individual_customers': individual_customers,
        'company_customers': company_customers,
        'price_a_customers': price_a_customers,
        'price_aa_customers': price_aa_customers,
        'price_aaa_customers': price_aaa_customers,
        'status_filter': status_filter,
        'customer_type_filter': customer_type_filter,
        'price_tier_filter': price_tier_filter,
        'search_query': search_query,
        'status_choices': Customer.Status.choices,
        'customer_type_choices': Customer.CustomerType.choices,
        'price_tier_choices': Customer.PriceTier.choices,
    }
    
    return render(request, 'customers/customer_list.html', context)

@login_required
def customer_detail(request, customer_id):
    """แสดงรายละเอียดลูกค้า"""
    customer = get_object_or_404(Customer, id=customer_id)
    
    # ประวัติการติดต่อ
    contact_histories = CustomerContactHistory.objects.filter(customer=customer).order_by('-contact_date')
    
    # ข้อมูลออเดอร์ (ถ้ามี)
    try:
        from App_OrderingProductForSale.models import OrderRequest, Invoice
        # ดึงออเดอร์ของลูกค้า
        recent_orders = OrderRequest.objects.filter(customer=customer).order_by('-created_at')[:5]
        total_orders = OrderRequest.objects.filter(customer=customer).count()
        
        # คำนวณยอดขายรวมจากใบแจ้งหนี้
        total_order_amount = Invoice.objects.filter(
            order_request__customer=customer
        ).aggregate(total=Sum('grand_total'))['total'] or 0
        
        # ออเดอร์ที่รอดำเนินการ
        pending_orders = OrderRequest.objects.filter(
            customer=customer, 
            status=OrderRequest.Status.PENDING
        ).count()
        
        # ออเดอร์ที่เสร็จสิ้นแล้ว
        completed_orders = OrderRequest.objects.filter(
            customer=customer, 
            status=OrderRequest.Status.COMPLETED
        ).count()
        
    except ImportError:
        recent_orders = []
        total_orders = 0
        total_order_amount = 0
        pending_orders = 0
        completed_orders = 0
    
    context = {
        'customer': customer,
        'contact_histories': contact_histories,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'total_order_amount': total_order_amount,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
    }
    
    return render(request, 'customers/customer_detail.html', context)


@login_required
def customer_add(request):
    """เพิ่มลูกค้าใหม่"""
    if request.method == 'POST':
        try:
            # ข้อมูลทั่วไป
            name = request.POST.get('name')
            customer_code = request.POST.get('customer_code')
            customer_type = request.POST.get('customer_type')
            status = request.POST.get('status', 'active')
            
            # ข้อมูลผู้ติดต่อ
            contact_name = request.POST.get('contact_name', '')
            contact_title = request.POST.get('contact_title', '')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            fax_number = request.POST.get('fax_number')
            website = request.POST.get('website')
            
            # ข้อมูลที่อยู่
            address = request.POST.get('address')
            city = request.POST.get('city')
            state = request.POST.get('state')
            postal_code = request.POST.get('postal_code')
            country = request.POST.get('country', 'ไทย')
            
            # ข้อมูลการเงิน
            tax_id = request.POST.get('tax_id')
            bank_name = request.POST.get('bank_name')
            bank_account_number = request.POST.get('bank_account_number')
            price_tier = request.POST.get('price_tier', 'A')
            credit_limit = request.POST.get('credit_limit', 0)
            payment_terms = request.POST.get('payment_terms')
            credit_term = request.POST.get('credit_term', 0)
            
            # ข้อมูลเพิ่มเติม
            notes = request.POST.get('notes')
            
            # ตรวจสอบว่ารหัสลูกค้าซ้ำหรือไม่ (ถ้ามีการระบุ)
            if customer_code and Customer.objects.filter(customer_code=customer_code).exists():
                messages.error(request, f'รหัสลูกค้า {customer_code} มีอยู่ในระบบแล้ว')
                return redirect('customers:customer_add')
            
            # สร้างลูกค้าใหม่
            customer = Customer.objects.create(
                name=name,
                customer_code=customer_code,
                customer_type=customer_type,
                status=status,
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
                tax_id=tax_id,
                bank_name=bank_name,
                bank_account_number=bank_account_number,
                price_tier=price_tier,
                credit_limit=credit_limit,
                payment_terms=payment_terms,
                credit_term=credit_term,
                notes=notes
            )
            
            messages.success(request, f'เพิ่มลูกค้า {name} เรียบร้อยแล้ว')
            return redirect('customers:customer_detail', customer_id=customer.id)
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    context = {
        'customer_type_choices': Customer.CustomerType.choices,
        'status_choices': Customer.Status.choices,
        'price_tier_choices': Customer.PriceTier.choices,
    }
    
    return render(request, 'customers/customer_add.html', context)

@login_required
def customer_edit(request, customer_id):
    """แก้ไขข้อมูลลูกค้า"""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        try:
            # ข้อมูลทั่วไป
            customer.name = request.POST.get('name')
            customer.customer_type = request.POST.get('customer_type')
            customer.status = request.POST.get('status')
            
            # ข้อมูลผู้ติดต่อ
            customer.contact_name = request.POST.get('contact_name', '')
            customer.contact_title = request.POST.get('contact_title', '')
            customer.email = request.POST.get('email')
            customer.phone_number = request.POST.get('phone_number')
            customer.fax_number = request.POST.get('fax_number')
            customer.website = request.POST.get('website')
            
            # ข้อมูลที่อยู่
            customer.address = request.POST.get('address')
            customer.city = request.POST.get('city')
            customer.state = request.POST.get('state')
            customer.postal_code = request.POST.get('postal_code')
            customer.country = request.POST.get('country', 'ไทย')
            
            # ข้อมูลการเงิน
            customer.tax_id = request.POST.get('tax_id')
            customer.bank_name = request.POST.get('bank_name')
            customer.bank_account_number = request.POST.get('bank_account_number')
            customer.price_tier = request.POST.get('price_tier')
            customer.credit_limit = request.POST.get('credit_limit', 0)
            customer.payment_terms = request.POST.get('payment_terms')
            customer.credit_term = request.POST.get('credit_term', 0)
            
            # ข้อมูลเพิ่มเติม
            customer.notes = request.POST.get('notes')
            
            customer.save()
            messages.success(request, f'อัปเดตข้อมูลลูกค้า {customer.name} เรียบร้อยแล้ว')
            return redirect('customers:customer_detail', customer_id=customer.id)
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    context = {
        'customer': customer,
        'customer_type_choices': Customer.CustomerType.choices,
        'status_choices': Customer.Status.choices,
        'price_tier_choices': Customer.PriceTier.choices,
    }
    
    return render(request, 'customers/customer_edit.html', context)


@login_required
def add_contact_history(request, customer_id):
    """เพิ่มประวัติการติดต่อ"""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        try:
            contact_type = request.POST.get('contact_type')
            contact_date_str = request.POST.get('contact_date')
            subject = request.POST.get('subject')
            description = request.POST.get('description')
            
            # ถ้าไม่มีวันที่ ให้ใช้วันที่ปัจจุบัน
            if contact_date_str:
                try:
                    # รองรับรูปแบบวันที่แบบ ISO (HTML datetime-local)
                    if 'T' in contact_date_str:
                        contact_date = timezone.datetime.strptime(contact_date_str, '%Y-%m-%dT%H:%M')
                    # รองรับรูปแบบวันที่แบบเดิม
                    else:
                        contact_date = timezone.datetime.strptime(contact_date_str, '%Y-%m-%d %H:%M')
                    
                    # แปลงเป็น timezone-aware datetime
                    contact_date = timezone.make_aware(contact_date)
                except ValueError:
                    # ถ้าแปลงไม่ได้ ให้ใช้วันที่ปัจจุบัน
                    messages.warning(request, f'รูปแบบวันที่ไม่ถูกต้อง ระบบใช้วันที่ปัจจุบันแทน')
                    contact_date = timezone.now()
            else:
                contact_date = timezone.now()
            
            CustomerContactHistory.objects.create(
                customer=customer,
                contact_type=contact_type,
                contact_date=contact_date,
                subject=subject,
                description=description,
                contacted_by=request.user
            )
            
            messages.success(request, 'เพิ่มประวัติการติดต่อเรียบร้อยแล้ว')
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return redirect('customers:customer_detail', customer_id=customer_id)


@login_required
def delete_contact_history(request, customer_id, contact_id):
    """ลบประวัติการติดต่อ"""
    customer = get_object_or_404(Customer, id=customer_id)
    contact_history = get_object_or_404(CustomerContactHistory, id=contact_id, customer=customer)
    
    if request.method == 'POST':
        contact_history.delete()
        messages.success(request, 'ลบประวัติการติดต่อเรียบร้อยแล้ว')
    
    return redirect('customers:customer_detail', customer_id=customer_id)


@login_required
def customer_reports(request):
    """รายงานและสถิติลูกค้า"""
    # ข้อมูลสรุป
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(status='active').count()
    
    # จำนวนลูกค้าแต่ละประเภท
    customer_by_type = Customer.objects.values('customer_type').annotate(
        count=Count('id')
    ).order_by('customer_type')
    
    # จำนวนลูกค้าแต่ละสถานะ
    customer_by_status = Customer.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # จำนวนลูกค้าแต่ละระดับราคา
    customer_by_price_tier = Customer.objects.values('price_tier').annotate(
        count=Count('id')
    ).order_by('price_tier')
    
    # ลูกค้าตามจังหวัด
    customer_by_state = Customer.objects.values('state').annotate(
        count=Count('id')
    ).exclude(state__isnull=True).exclude(state='').order_by('-count')[:10]
    
    # การติดต่อแยกตามประเภท
    contact_by_type = CustomerContactHistory.objects.values('contact_type').annotate(count=Count('id'))
    contact_type_data = {item['contact_type']: item['count'] for item in contact_by_type}
    
    # สร้างข้อมูลตามสถานะสำหรับแผนภูมิ
    customer_status_data = Customer.objects.values('status').annotate(count=Count('id'))
    status_data = {item['status']: item['count'] for item in customer_status_data}
    
    # สร้างข้อมูลตามประเภทสำหรับแผนภูมิ
    customer_type_data = Customer.objects.values('customer_type').annotate(count=Count('id'))
    type_data = {item['customer_type']: item['count'] for item in customer_type_data}
    
    # สร้างข้อมูลตามระดับราคาสำหรับแผนภูมิ
    customer_price_tier_data = Customer.objects.values('price_tier').annotate(count=Count('id'))
    price_tier_data = {item['price_tier']: item['count'] for item in customer_price_tier_data}
    
    # การติดต่อในช่วง 30 วันที่ผ่านมา
    last_30_days = timezone.now() - timedelta(days=30)
    recent_contacts = CustomerContactHistory.objects.filter(
        contact_date__gte=last_30_days
    ).count()
    
    # จำนวนการติดต่อเฉลี่ยต่อลูกค้า
    try:
        total_contacts = CustomerContactHistory.objects.count()
        customers_with_contact = CustomerContactHistory.objects.values('customer').distinct().count()
        avg_contacts_per_customer = total_contacts / customers_with_contact if customers_with_contact > 0 else 0
    except:
        avg_contacts_per_customer = 0
    
    # ลูกค้าที่มีการติดต่อมากที่สุด 10 อันดับแรก
    top_contacted_customers = Customer.objects.annotate(
        contact_count=Count('contact_histories')
    ).order_by('-contact_count')[:10]
    
    # ลูกค้าที่เพิ่มใหม่ในแต่ละเดือน (6 เดือนล่าสุด)
    six_months_ago = timezone.now() - timedelta(days=180)
    customers_by_month = Customer.objects.filter(
        created_at__gte=six_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # ประวัติการติดต่อรายเดือน
    now = timezone.now()
    month_data = []
    
    for i in range(11, -1, -1):
        month_date = now - timedelta(days=30*i)
        month_name = month_date.strftime('%B %Y')
        month_contacts = CustomerContactHistory.objects.filter(
            contact_date__year=month_date.year,
            contact_date__month=month_date.month
        ).count()
        month_data.append({
            'month': month_name,
            'count': month_contacts
        })
    
    # ลูกค้าที่มีออเดอร์มากที่สุด และมูลค่ามากที่สุด (ถ้ามี)
    try:
        from App_OrderingProductForSale.models import OrderRequest
        
        top_ordered_customers = Customer.objects.annotate(
            order_count=Count('orderrequest')
        ).order_by('-order_count')[:10]
        
        # ลูกค้าที่มีมูลค่าการสั่งซื้อมากที่สุด
        try:
            top_value_customers = Customer.objects.annotate(
                total_value=Sum('orderrequest__total_amount')
            ).order_by('-total_value')[:10]
        except:
            top_value_customers = []
            
        # ข้อมูลรายเดือนของออเดอร์จากลูกค้า
        month_orders = []
        for i in range(11, -1, -1):
            month_date = now - timedelta(days=30*i)
            month_name = month_date.strftime('%B %Y')
            try:
                month_order_count = OrderRequest.objects.filter(
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
        top_ordered_customers = []
        top_value_customers = []
        month_orders = []
    
    # ลูกค้าที่ไม่มีการติดต่อในช่วง 3 เดือนที่ผ่านมา
    three_months_ago = now - timedelta(days=90)
    inactive_customers = Customer.objects.filter(status='active').exclude(
        id__in=CustomerContactHistory.objects.filter(
            contact_date__gte=three_months_ago
        ).values_list('customer_id', flat=True)
    )
    
    # สรุปข้อมูลเครดิต
    credit_summary = Customer.objects.aggregate(
        total_credit=Sum('credit_limit'),
        avg_credit=Avg('credit_limit')
    )
    
    context = {
        'page_title': 'รายงานลูกค้า',
        'total_customers': total_customers,
        'active_customers': active_customers,
        'customer_by_type': customer_by_type,
        'customer_by_status': customer_by_status,
        'customer_by_price_tier': customer_by_price_tier,
        'customer_by_state': customer_by_state,
        'contact_type_data': contact_type_data,
        'status_data': status_data,
        'type_data': type_data,
        'price_tier_data': price_tier_data,
        'recent_contacts': recent_contacts,
        'avg_contacts_per_customer': round(avg_contacts_per_customer, 2),
        'top_contacted_customers': top_contacted_customers,
        'top_ordered_customers': top_ordered_customers,
        'top_value_customers': top_value_customers,
        'customers_by_month': customers_by_month,
        'month_data': month_data,
        'month_orders': month_orders,
        'inactive_customers': inactive_customers,
        'credit_summary': credit_summary,
    }
    
    return render(request, 'customers/customer_reports.html', context)


@login_required
def export_customers(request):
    """ส่งออกข้อมูลลูกค้าเป็น CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="customers_export_{}.csv"'.format(
        timezone.now().strftime('%Y%m%d_%H%M%S')
    )
    response.write('\ufeff')  # BOM for UTF-8
    
    # ฟิลเตอร์
    customer_type = request.GET.get('customer_type')
    status = request.GET.get('status')
    price_tier = request.GET.get('price_tier')
    
    customers = Customer.objects.all()
    
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
    
    if status:
        customers = customers.filter(status=status)
        
    if price_tier:
        customers = customers.filter(price_tier=price_tier)
    
    writer = csv.writer(response)
    
    # Header
    writer.writerow([
        'รหัสลูกค้า', 'ชื่อลูกค้า/บริษัท', 'ประเภทลูกค้า', 'สถานะ',
        'ชื่อผู้ติดต่อ', 'ตำแหน่ง', 'อีเมล', 'โทรศัพท์', 'แฟกซ์', 'เว็บไซต์',
        'ที่อยู่', 'เมือง/อำเภอ', 'จังหวัด', 'รหัสไปรษณีย์', 'ประเทศ',
        'เลขประจำตัวผู้เสียภาษี', 'ธนาคาร', 'เลขที่บัญชี', 'ระดับราคา',
        'วงเงินเครดิต', 'เงื่อนไขการชำระเงิน', 'เครดิตเทอม',
        'วันที่สร้าง', 'วันที่อัปเดตล่าสุด', 'จำนวนครั้งที่ติดต่อ', 'วันที่ติดต่อล่าสุด'
    ])
    
    # Data
    for customer in customers.order_by('name'):
        # หาข้อมูลประวัติการติดต่อ
        contact_count = CustomerContactHistory.objects.filter(customer=customer).count()
        try:
            latest_contact = CustomerContactHistory.objects.filter(customer=customer).latest('contact_date')
            latest_contact_date = latest_contact.contact_date.strftime('%Y-%m-%d')
        except:
            latest_contact_date = 'ไม่มีข้อมูล'
        
        writer.writerow([
            customer.customer_code,
            customer.name,
            customer.get_customer_type_display(),
            customer.get_status_display(),
            customer.contact_name,
            customer.contact_title,
            customer.email,
            customer.phone_number,
            customer.fax_number,
            customer.website,
            customer.address,
            customer.city,
            customer.state,
            customer.postal_code,
            customer.country,
            customer.tax_id,
            customer.bank_name,
            customer.bank_account_number,
            customer.get_price_tier_display(),
            customer.credit_limit,
            customer.payment_terms,
            customer.credit_term,
            customer.created_at.strftime('%Y-%m-%d %H:%M:%S') if customer.created_at else '',
            customer.updated_at.strftime('%Y-%m-%d %H:%M:%S') if customer.updated_at else '',
            contact_count,
            latest_contact_date
        ])
    
    return response
