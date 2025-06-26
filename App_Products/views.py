from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField, Count, Avg, Min, Max
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Product, Category, Brand
from django.utils import timezone
from django.db.models.functions import TruncMonth
import csv
from datetime import datetime, timedelta

# ============================================
#  Dashboard Views
# ============================================

@login_required
def product_dashboard(request):
    """
    Product dashboard with analytics and statistics
    """
    # Basic statistics
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_brands = Brand.objects.count()
    
    # Product statistics by status (if inventory exists)
    try:
        from App_Inventory.models import InventoryItem
        total_inventory_items = InventoryItem.objects.count()
        available_items = InventoryItem.objects.filter(status='available').count()
        reserved_items = InventoryItem.objects.filter(status='reserved').count()
        sold_items = InventoryItem.objects.filter(status='sold').count()
        damaged_items = InventoryItem.objects.filter(status='damaged').count()
        expired_items = InventoryItem.objects.filter(status='expired').count()
    except ImportError:
        total_inventory_items = 0
        available_items = 0
        reserved_items = 0
        sold_items = 0
        damaged_items = 0
        expired_items = 0
    
    # Price statistics
    price_stats = Product.objects.aggregate(
        avg_cost=Avg('cost_price'),
        avg_price_a=Avg('price_a'),
        avg_price_aa=Avg('price_aa'),
        avg_price_aaa=Avg('price_aaa'),
        min_price=Min('price_a'),
        max_price=Max('price_a'),
        min_cost=Min('cost_price'),
        max_cost=Max('cost_price')
    )
    
    # Products with good profit margins (above 30%)
    profitable_products = Product.objects.filter(
        cost_price__gt=0,
        price_a__gt=F('cost_price')
    ).annotate(
        profit_margin=ExpressionWrapper(
            ((F('price_a') - F('cost_price')) / F('price_a')) * 100,
            output_field=DecimalField(max_digits=5, decimal_places=2)
        )
    ).filter(profit_margin__gt=30).count()
    
    # Low profit or loss products (under 10% margin)
    low_profit_products = Product.objects.filter(
        cost_price__gt=0,
        price_a__gt=F('cost_price')
    ).annotate(
        profit_margin=ExpressionWrapper(
            ((F('price_a') - F('cost_price')) / F('price_a')) * 100,
            output_field=DecimalField(max_digits=5, decimal_places=2)
        )
    ).filter(profit_margin__lt=10).count()
    
    # Recent products (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_products = Product.objects.filter(
        created_at__gte=thirty_days_ago
    ).select_related('category', 'brand').order_by('-created_at')[:10]
    
    new_products_count = Product.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()
    
    # Products by category
    products_by_category = Category.objects.annotate(
        count=Count('product')
    ).order_by('-count')[:10]
    
    # Products by brand
    products_by_brand = Brand.objects.annotate(
        count=Count('product')
    ).order_by('-count')[:10]
    
    # Empty categories and brands
    empty_categories = Category.objects.annotate(
        product_count=Count('product')
    ).filter(product_count=0).count()
    
    empty_brands = Brand.objects.annotate(
        product_count=Count('product')
    ).filter(product_count=0).count()
    
    # Most expensive and cheapest products
    highest_price_product = Product.objects.filter(price_a__gt=0).order_by('-price_a').first()
    lowest_price_product = Product.objects.filter(price_a__gt=0).order_by('price_a').first()
    
    # Price ranges for distribution
    price_ranges = [
        {'range_label': '0-100 บาท', 'count': Product.objects.filter(price_a__lt=100).count()},
        {'range_label': '100-500 บาท', 'count': Product.objects.filter(price_a__gte=100, price_a__lt=500).count()},
        {'range_label': '500-1,000 บาท', 'count': Product.objects.filter(price_a__gte=500, price_a__lt=1000).count()},
        {'range_label': '1,000-5,000 บาท', 'count': Product.objects.filter(price_a__gte=1000, price_a__lt=5000).count()},
        {'range_label': '5,000+ บาท', 'count': Product.objects.filter(price_a__gte=5000).count()},
    ]
    
    # Top profit products (profit margin > 0)
    top_profit_products = Product.objects.filter(
        cost_price__gt=0,
        price_a__gt=F('cost_price')
    ).annotate(
        profit_margin=ExpressionWrapper(
            ((F('price_a') - F('cost_price')) / F('price_a')) * 100,
            output_field=DecimalField(max_digits=5, decimal_places=2)
        )
    ).order_by('-profit_margin')[:5]
    
    # Products that need reorder
    products_need_reorder = Product.objects.filter(reorder_point__gt=0).count()
    
    context = {
        'page_title': 'ภาพรวมสินค้า',
        'total_products': total_products,
        'total_categories': total_categories,
        'total_brands': total_brands,
        'empty_categories': empty_categories,
        'empty_brands': empty_brands,
        'new_products_count': new_products_count,
        'profitable_products': profitable_products,
        'low_profit_products': low_profit_products,
        'products_need_reorder': products_need_reorder,
        'recent_products': recent_products,
        'products_by_category': products_by_category,
        'products_by_brand': products_by_brand,
        'highest_price_product': highest_price_product,
        'lowest_price_product': lowest_price_product,
        'price_ranges': price_ranges,
        'top_profit_products': top_profit_products,
        'price_stats': price_stats,
        # Inventory stats (if available)
        'total_inventory_items': total_inventory_items,
        'available_items': available_items,
        'reserved_items': reserved_items,
        'sold_items': sold_items,
        'damaged_items': damaged_items,
        'expired_items': expired_items,
    }
    
    return render(request, 'products/dashboard.html', context)

@login_required
def product_reports(request):
    """
    Product reports with detailed analytics
    """
    # Filter parameters
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    products = Product.objects.all()
    
    # Apply filters
    if category_id:
        products = products.filter(category_id=category_id)
    if brand_id:
        products = products.filter(brand_id=brand_id)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            products = products.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            products = products.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Analytics
    total_products = products.count()
    
    # Price analysis
    price_analysis = products.aggregate(
        min_cost=Min('cost_price'),
        max_cost=Max('cost_price'),
        avg_cost=Avg('cost_price'),
        min_price_a=Min('price_a'),
        max_price_a=Max('price_a'),
        avg_price_a=Avg('price_a'),
        total_value=Sum(F('cost_price') * F('reorder_point'))
    )
    
    # Stock analysis
    stock_analysis = products.aggregate(
        total_reorder_points=Sum('reorder_point'),
        avg_reorder_point=Avg('reorder_point'),
        avg_reorder_quantity=Avg('reorder_quantity'),
        zero_reorder_count=Count('id', filter=Q(reorder_point=0)),
        high_reorder_count=Count('id', filter=Q(reorder_point__gte=100))
    )
    
    # Category breakdown
    category_breakdown = products.values(
        'category__name'
    ).annotate(
        product_count=Count('id'),
        avg_price=Avg('price_a'),
        avg_cost=Avg('cost_price')
    ).order_by('-product_count')
    
    # Brand breakdown
    brand_breakdown = products.values(
        'brand__name'
    ).annotate(
        product_count=Count('id'),
        avg_price=Avg('price_a'),
        avg_cost=Avg('cost_price')
    ).order_by('-product_count')
    
    # Top products by price
    top_products_by_value = products.filter(price_a__gt=0).order_by('-price_a')[:20]
    
    # Top profit products
    top_profit_products = products.filter(
        cost_price__gt=0,
        price_a__gt=F('cost_price')
    ).annotate(
        profit_margin=ExpressionWrapper(
            ((F('price_a') - F('cost_price')) / F('price_a')) * 100,
            output_field=DecimalField(max_digits=5, decimal_places=2)
        )
    ).order_by('-profit_margin')[:20]
    
    # Price distribution
    price_distribution = [
        {'range': 'น้อยกว่า 1,000', 'count': products.filter(price_a__lt=1000).count()},
        {'range': '1,000 - 4,999', 'count': products.filter(price_a__gte=1000, price_a__lt=5000).count()},
        {'range': '5,000 - 9,999', 'count': products.filter(price_a__gte=5000, price_a__lt=10000).count()},
        {'range': '10,000 - 19,999', 'count': products.filter(price_a__gte=10000, price_a__lt=20000).count()},
        {'range': '20,000 ขึ้นไป', 'count': products.filter(price_a__gte=20000).count()},
    ]
    
    # Price ranges for chart compatibility  
    price_ranges = [
        {'range_label': 'น้อยกว่า 1,000', 'count': products.filter(price_a__lt=1000).count()},
        {'range_label': '1,000 - 4,999', 'count': products.filter(price_a__gte=1000, price_a__lt=5000).count()},
        {'range_label': '5,000 - 9,999', 'count': products.filter(price_a__gte=5000, price_a__lt=10000).count()},
        {'range_label': '10,000 - 19,999', 'count': products.filter(price_a__gte=10000, price_a__lt=20000).count()},
        {'range_label': '20,000 ขึ้นไป', 'count': products.filter(price_a__gte=20000).count()},
    ]
    
    # Recent products (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_products = products.filter(
        created_at__gte=thirty_days_ago
    ).order_by('-created_at')[:10]
    
    # Most expensive and cheapest products
    most_expensive_products = products.filter(price_a__gt=0).order_by('-price_a')[:10]
    cheapest_products = products.filter(price_a__gt=0).order_by('price_a')[:10]
    
    # Products by category summary
    products_by_category = Category.objects.annotate(
        count=Count('product')
    ).order_by('-count')[:10]
    
    # Products by brand summary  
    products_by_brand = Brand.objects.annotate(
        count=Count('product')
    ).order_by('-count')[:10]
    
    # Empty categories and brands
    empty_categories = Category.objects.annotate(
        product_count=Count('product')
    ).filter(product_count=0)
    
    empty_brands = Brand.objects.annotate(
        product_count=Count('product')
    ).filter(product_count=0)
    
    # Monthly trends (last 12 months)
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_trends = products.filter(
        created_at__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        products_added=Count('id'),
        avg_cost_price=Avg('cost_price'),
        avg_selling_price=Avg('price_a')
    ).order_by('month')
    
    # Get all categories and brands for filters
    categories = Category.objects.all().order_by('name')
    brands = Brand.objects.all().order_by('name')
    
    # For template compatibility
    total_categories = Category.objects.count()
    total_brands = Brand.objects.count()
    price_stats = price_analysis  # alias for template compatibility
    
    context = {
        'page_title': 'รายงานสินค้า',
        'total_products': total_products,
        'total_categories': total_categories,
        'total_brands': total_brands,
        'price_analysis': price_analysis,
        'price_stats': price_stats,
        'stock_analysis': stock_analysis,
        'category_breakdown': category_breakdown,
        'brand_breakdown': brand_breakdown,
        'top_products_by_value': top_products_by_value,
        'top_profit_products': top_profit_products,
        'price_distribution': price_distribution,
        'price_ranges': price_ranges,  # เพิ่มสำหรับ template compatibility
        'recent_products': recent_products,
        'most_expensive_products': most_expensive_products,
        'cheapest_products': cheapest_products,
        'products_by_category': products_by_category,
        'products_by_brand': products_by_brand,
        'empty_categories': empty_categories,
        'empty_brands': empty_brands,
        'monthly_trends': monthly_trends,
        'categories': categories,
        'brands': brands,
        'filters': {
            'category_id': category_id,
            'brand_id': brand_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'products/reports.html', context)

@login_required
def export_products(request):
    """
    Export products data to CSV
    """
    # Get all products
    products = Product.objects.select_related('category', 'brand')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
    
    # Add BOM for Excel UTF-8 support
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'รหัสสินค้า (SKU)',
        'ชื่อสินค้า',
        'รายละเอียด',
        'หมวดหมู่',
        'แบรนด์',
        'หน่วย',
        'ราคาทุน',
        'ราคาขาย A',
        'ราคาขาย AA',
        'ราคาขาย AAA',
        'จุดสั่งซื้อใหม่',
        'จำนวนสั่งซื้อ',
        'วันที่สร้าง',
        'วันที่อัปเดต'
    ])
    
    # Write data
    for product in products:
        writer.writerow([
            product.sku or '',
            product.name,
            product.description or '',
            product.category.name if product.category else '',
            product.brand.name if product.brand else '',
            product.unit,
            float(product.cost_price),
            float(product.price_a),
            float(product.price_aa),
            float(product.price_aaa),
            product.reorder_point,
            product.reorder_quantity,
            product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            product.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

# ============================================
#  Product Views
# ============================================

@login_required
def product_list(request):
    """
    Display a list of all products with search and filter functionality
    """
    # Get all products ordered by name
    products = Product.objects.all().order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by category
    category_id = request.GET.get('category', '')
    if category_id and category_id.isdigit():
        products = products.filter(category_id=category_id)
    
    # Filter by brand
    brand_id = request.GET.get('brand', '')
    if brand_id and brand_id.isdigit():
        products = products.filter(brand_id=brand_id)
    
    # Apply sorting
    sort_param = request.GET.get('sort', '-created_at')
    if sort_param in ['name', '-name', 'sku', '-sku', 'created_at', '-created_at']:
        products = products.order_by(sort_param)
    
    # Pagination
    paginator = Paginator(products, 10)  # Show 10 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all categories and brands for filters
    categories = Category.objects.all().order_by('name')
    brands = Brand.objects.all().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'brands': brands,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_brand': brand_id,
        'sort': sort_param,
    }
    
    return render(request, 'products/product_list.html', context)

@login_required
def product_detail(request, product_id):
    """
    Display detailed information about a specific product
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Get current pricing information
    current_price = product.get_current_price()
    
    # Get all categories and brands for the form
    categories = Category.objects.all().order_by('name')
    brands = Brand.objects.all().order_by('name')
    
    context = {
        'product': product,
        'current_price': current_price,
        'categories': categories,
        'brands': brands,
    }
    
    return render(request, 'products/product_detail.html', context)

@login_required
@require_POST
def product_create(request):
    """
    Handle product creation form submission
    """
    try:
        # Extract data from form
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        description = request.POST.get('description', '')
        category_id = request.POST.get('category', None)
        brand_id = request.POST.get('brand', None)
        unit = request.POST.get('unit')
        
        # Convert pricing data to decimal
        cost_price = request.POST.get('cost_price', 0)
        price_a = request.POST.get('price_a', 0)
        price_aa = request.POST.get('price_aa', 0)
        price_aaa = request.POST.get('price_aaa', 0)
        
        # Stock information
        reorder_point = request.POST.get('reorder_point', 0)
        reorder_quantity = request.POST.get('reorder_quantity', 0)
        
        # Create new product
        product = Product(
            name=name,
            description=description,
            unit=unit,
            cost_price=cost_price,
            price_a=price_a,
            price_aa=price_aa,
            price_aaa=price_aaa,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity
        )
        
        # Only set SKU if provided and not empty
        if sku and sku.strip():
            product.sku = sku.strip()
        # Otherwise, SKU will be auto-generated in the save method
            
        # Set category and brand if provided
        if category_id:
            product.category_id = category_id
        if brand_id:
            product.brand_id = brand_id
            
        # Save the product
        product.save()
        
        messages.success(request, f'สร้างสินค้า "{product.name}" สำเร็จ')
        return redirect('products:product_detail', product_id=product.id)
        
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        return redirect('products:product_list')

@login_required
@require_POST
def product_update(request, product_id):
    """
    Handle product update form submission
    """
    product = get_object_or_404(Product, id=product_id)
    
    try:
        # Extract data from form
        product.name = request.POST.get('name')
        product.description = request.POST.get('description', '')
        
        category_id = request.POST.get('category', None)
        product.category_id = category_id if category_id else None
        
        brand_id = request.POST.get('brand', None)
        product.brand_id = brand_id if brand_id else None
        
        product.unit = request.POST.get('unit')
        
        # Convert pricing data to decimal
        product.cost_price = request.POST.get('cost_price', 0)
        product.price_a = request.POST.get('price_a', 0)
        product.price_aa = request.POST.get('price_aa', 0)
        product.price_aaa = request.POST.get('price_aaa', 0)
        
        # Stock information
        product.reorder_point = request.POST.get('reorder_point', 0)
        product.reorder_quantity = request.POST.get('reorder_quantity', 0)
        
        # Save the product
        product.save()
        
        messages.success(request, f'อัปเดตสินค้า "{product.name}" สำเร็จ')
        return redirect('products:product_detail', product_id=product.id)
        
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        return redirect('products:product_detail', product_id=product_id)

# ============================================
#  Category Views
# ============================================

@login_required
def category_list(request):
    """
    Display a list of all categories with search functionality
    """
    # Get all categories ordered by name
    categories = Category.objects.all().order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(categories, 10)  # Show 10 categories per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'products/category_list.html', context)

@login_required
def category_detail(request, category_id):
    """
    Display detailed information about a specific category
    """
    category = get_object_or_404(Category, id=category_id)
    
    # Get products in this category
    products = Product.objects.filter(category=category).order_by('name')
    
    # Pagination for products
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    
    context = {
        'category': category,
        'page_obj': page_obj,
        'total_products': products.count(),
        'products': page_obj,  # Add products for the template
    }
    
    return render(request, 'products/category_detail.html', context)

@login_required
@require_POST
def category_create(request):
    """
    Handle category creation form submission
    """
    try:
        # Extract data from form
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category_code = request.POST.get('category_code', '000')
        
        # Create new category
        category = Category(
            name=name,
            description=description,
            category_code=category_code
        )
        
        # Save the category
        category.save()
        
        messages.success(request, f'สร้างหมวดหมู่ "{category.name}" สำเร็จ')
        return redirect('products:category_detail', category_id=category.id)
        
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        return redirect('products:category_list')

@login_required
@require_POST
def category_update(request, category_id):
    """
    Handle category update form submission
    """
    category = get_object_or_404(Category, id=category_id)
    
    try:
        # Extract data from form
        category.name = request.POST.get('name')
        category.description = request.POST.get('description', '')
        category.category_code = request.POST.get('category_code', '000')
        
        # Save the category
        category.save()
        
        messages.success(request, f'อัปเดตหมวดหมู่ "{category.name}" สำเร็จ')
        return redirect('products:category_detail', category_id=category.id)
        
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        return redirect('products:category_detail', category_id=category_id)

# ============================================
#  Brand Views
# ============================================

@login_required
def brand_list(request):
    """
    Display a list of all brands with search functionality
    """
    # Get all brands ordered by name
    brands = Brand.objects.all().order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        brands = brands.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(brands, 10)  # Show 10 brands per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'products/brand_list.html', context)

@login_required
def brand_detail(request, brand_id):
    """
    Display detailed information about a specific brand
    """
    brand = get_object_or_404(Brand, id=brand_id)
    
    # Get products for this brand
    products = Product.objects.filter(brand=brand).order_by('name')
    
    # Pagination for products
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'brand': brand,
        'page_obj': page_obj,
        'products': page_obj,  # Add products for the template
        'total_products': products.count(),
    }
    
    return render(request, 'products/brand_detail.html', context)

@login_required
@require_POST
def brand_create(request):
    """
    Handle brand creation form submission
    """
    try:
        # Extract data from form
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        brand_code = request.POST.get('brand_code', '0000')
        
        # Create new brand
        brand = Brand(
            name=name,
            description=description,
            brand_code=brand_code
        )
        
        # Save the brand
        brand.save()
        
        messages.success(request, f'สร้างแบรนด์ "{brand.name}" สำเร็จ')
        return redirect('products:brand_detail', brand_id=brand.id)
        
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        return redirect('products:brand_list')

@login_required
@require_POST
def brand_update(request, brand_id):
    """
    Handle brand update form submission
    """
    brand = get_object_or_404(Brand, id=brand_id)
    
    try:
        # Extract data from form
        brand.name = request.POST.get('name')
        brand.description = request.POST.get('description', '')
        brand.brand_code = request.POST.get('brand_code', '0000')
        
        # Save the brand
        brand.save()
        
        messages.success(request, f'อัปเดตแบรนด์ "{brand.name}" สำเร็จ')
        return redirect('products:brand_detail', brand_id=brand.id)
        
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        return redirect('products:brand_detail', brand_id=brand_id)

# ============================================
#  Test Views
# ============================================

@login_required
def test_sku_generation(request):
    """
    Test function for SKU generation
    """
    if not request.user.is_superuser:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('products:product_list')
    
    try:
        # Create a test product with minimal data
        test_product = Product(
            name="ทดสอบ SKU อัตโนมัติ " + timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            unit="ชิ้น",
            cost_price=100,
            price_a=120,
            price_aa=110,
            price_aaa=100
        )
        
        # Set category and brand if they exist
        try:
            category = Category.objects.first()
            if category:
                test_product.category = category
        except:
            pass
            
        try:
            brand = Brand.objects.first()
            if brand:
                test_product.brand = brand
        except:
            pass
        
        # Save to trigger SKU generation
        test_product.save()
        
        messages.success(request, f'สร้าง SKU สำเร็จ: {test_product.sku}')
        return redirect('products:product_detail', product_id=test_product.id)
        
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาดในการสร้าง SKU: {str(e)}')
        return redirect('products:product_list')

@login_required
def brand_add(request):
    """
    Display a form to add a new brand
    """
    return render(request, 'products/brand_add.html')

@login_required
def brand_edit(request, brand_id):
    """
    Display a form to edit an existing brand
    """
    brand = get_object_or_404(Brand, id=brand_id)
    context = {
        'brand': brand
    }
    return render(request, 'products/brand_edit.html', context)

@login_required
def category_add(request):
    """
    Display a form to add a new category
    """
    return render(request, 'products/category_add.html')

@login_required
def category_edit(request, category_id):
    """
    Display a form to edit an existing category
    """
    category = get_object_or_404(Category, id=category_id)
    context = {
        'category': category
    }
    return render(request, 'products/category_edit.html', context)

@login_required
@login_required
def product_add(request):
    """
    Display a form to add a new product
    """
    # Get all categories and brands for the form
    categories = Category.objects.all().order_by('name')
    brands = Brand.objects.all().order_by('name')
    
    # Check if a specific brand was selected (from brand detail page)
    selected_brand_id = request.GET.get('brand')
    selected_brand = None
    
    if selected_brand_id:
        try:
            selected_brand = Brand.objects.get(id=selected_brand_id)
        except Brand.DoesNotExist:
            pass
    
    context = {
        'categories': categories,
        'brands': brands,
        'selected_brand': selected_brand,
    }
    return render(request, 'products/product_add.html', context)

@login_required
def product_edit(request, product_id):
    """
    Display a form to edit an existing product
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Get all categories and brands for the form
    categories = Category.objects.all().order_by('name')
    brands = Brand.objects.all().order_by('name')
    
    context = {
        'product': product,
        'categories': categories,
        'brands': brands,
    }
    return render(request, 'products/product_edit.html', context)
