from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta

# Import models from other apps
from App_Products.models import Product, Category, Brand
from App_Customer.models import Customer
from App_Supplier.models import Supplier
from App_OrderingProductForSale.models import OrderRequest, Invoice
from App_Purchase.models import PurchaseOrder, PurchaseRequisition
from App_Inventory.models import InventoryItem

@login_required
def dashboard(request):
    """แสดงหน้า Dashboard หลักของระบบ Storems"""
    
    # ข้อมูลพื้นฐาน
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_30_days = today - timedelta(days=30)
    
    # === สถิติสินค้า ===
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_brands = Brand.objects.count()
    
    # สินค้าใหม่ในเดือนนี้
    new_products_this_month = Product.objects.filter(created_at__gte=this_month_start).count()
    
    # === สถิติลูกค้า ===
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(status='active').count()
    new_customers_this_month = Customer.objects.filter(created_at__gte=this_month_start).count()
    
    # === สถิติซัพพลายเออร์ ===
    total_suppliers = Supplier.objects.count()
    active_suppliers = Supplier.objects.filter(status='active').count()
    
    # === สถิติออเดอร์ (ขาย) ===
    total_orders = OrderRequest.objects.count()
    pending_orders = OrderRequest.objects.filter(status=OrderRequest.Status.PENDING).count()
    completed_orders = OrderRequest.objects.filter(status=OrderRequest.Status.COMPLETED).count()
    orders_this_month = OrderRequest.objects.filter(created_at__gte=this_month_start).count()
    
    # มูลค่าการขายเดือนนี้
    monthly_sales = Invoice.objects.filter(
        issue_date__gte=this_month_start
    ).aggregate(total=Sum('grand_total'))['total'] or 0
    
    # === สถิติการจัดซื้อ ===
    total_purchase_orders = PurchaseOrder.objects.count()
    pending_purchase_orders = PurchaseOrder.objects.filter(status=PurchaseOrder.Status.PENDING).count()
    
    # === สถิติคลังสินค้า ===
    try:
        total_inventory_items = InventoryItem.objects.count()
        available_items = InventoryItem.objects.filter(status=InventoryItem.Status.AVAILABLE).count()
        low_stock_items = InventoryItem.objects.filter(
            product__reorder_point__gt=0
        ).annotate(
            available_count=Count('id', filter=Q(status=InventoryItem.Status.AVAILABLE))
        ).filter(
            available_count__lte=F('product__reorder_point')
        ).count()
    except:
        total_inventory_items = 0
        available_items = 0
        low_stock_items = 0
    
    # === ข้อมูลกิจกรรมล่าสุด ===
    recent_orders = OrderRequest.objects.select_related('customer').order_by('-created_at')[:5]
    recent_purchase_orders = PurchaseOrder.objects.select_related('supplier').order_by('-created_at')[:5]
    
    # === สถิติรายวัน (7 วันล่าสุด) ===
    daily_stats = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_orders = OrderRequest.objects.filter(created_at__date=date).count()
        daily_sales = Invoice.objects.filter(issue_date=date).aggregate(
            total=Sum('grand_total')
        )['total'] or 0
        
        daily_stats.append({
            'date': date,
            'orders': daily_orders,
            'sales': float(daily_sales),
        })
    
    # === Top Performance ===
    # ลูกค้าที่สั่งซื้อมากที่สุด
    top_customers = Customer.objects.annotate(
        order_count=Count('orderrequest')
    ).filter(order_count__gt=0).order_by('-order_count')[:5]
    
    # ซัพพลายเออร์ที่ซื้อมากที่สุด
    top_suppliers = Supplier.objects.annotate(
        purchase_count=Count('purchase_orders')
    ).filter(purchase_count__gt=0).order_by('-purchase_count')[:5]
    
    # สินค้าที่ขายดี
    top_products = Product.objects.annotate(
        order_count=Count('order_details')
    ).filter(order_count__gt=0).order_by('-order_count')[:5]
    
    context = {
        'page_title': 'Dashboard - Storems',
        
        # สถิติหลัก
        'total_products': total_products,
        'total_categories': total_categories,
        'total_brands': total_brands,
        'new_products_this_month': new_products_this_month,
        
        'total_customers': total_customers,
        'active_customers': active_customers,
        'new_customers_this_month': new_customers_this_month,
        
        'total_suppliers': total_suppliers,
        'active_suppliers': active_suppliers,
        
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'orders_this_month': orders_this_month,
        'monthly_sales': monthly_sales,
        
        'total_purchase_orders': total_purchase_orders,
        'pending_purchase_orders': pending_purchase_orders,
        
        'total_inventory_items': total_inventory_items,
        'available_items': available_items,
        'low_stock_items': low_stock_items,
        
        # ข้อมูลเพิ่มเติม
        'recent_orders': recent_orders,
        'recent_purchase_orders': recent_purchase_orders,
        'daily_stats': daily_stats,
        'top_customers': top_customers,
        'top_suppliers': top_suppliers,
        'top_products': top_products,
        
        # วันที่
        'today': today,
        'this_month_start': this_month_start,
    }
    
    return render(request, 'general/dashboard.html', context)

@login_required
def permission_demo(request):
    """หน้าตัวอย่างการใช้งานระบบสิทธิ์"""
    return render(request, 'general/permission_demo.html')