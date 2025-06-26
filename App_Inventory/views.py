from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F, Sum, Avg, DecimalField, Case, When
from django.db.models.functions import TruncDate, TruncMonth
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta
from .models import InventoryItem, Location, StockCount, StockCountItem, DamagedItem, LocationHistory
from App_Products.models import Product
from decimal import Decimal

# ============================================
#  Dashboard Views
# ============================================

@login_required
def inventory_dashboard(request):
    """หน้าหลักของระบบคลังสินค้า แสดงภาพรวมและสถิติต่างๆ"""
    
    # จำนวนสินค้าทั้งหมดในคลัง แยกตามสถานะ
    inventory_stats = {
        'total': InventoryItem.objects.count(),
        'available': InventoryItem.objects.filter(status=InventoryItem.Status.AVAILABLE).count(),
        'reserved': InventoryItem.objects.filter(status=InventoryItem.Status.RESERVED).count(),
        'sold': InventoryItem.objects.filter(status=InventoryItem.Status.SOLD).count(),
        'damaged': InventoryItem.objects.filter(status=InventoryItem.Status.DAMAGED).count(),
        'expired': InventoryItem.objects.filter(status=InventoryItem.Status.EXPIRED).count(),
    }
    
    # สินค้าที่ต้องสั่งซื้อเพิ่ม (จำนวนน้อยกว่า reorder_point)
    low_stock_products = Product.objects.filter(
        reorder_point__gt=0
    ).annotate(
        available_count=Count(
            'inventoryitem', 
            filter=Q(inventoryitem__status=InventoryItem.Status.AVAILABLE)
        )
    ).filter(
        available_count__lt=F('reorder_point')
    ).order_by('name')[:5]  # แสดง 5 รายการ
    
    # สินค้าที่ใกล้หมดอายุ (30 วันข้างหน้า)
    thirty_days_from_now = timezone.now().date() + timezone.timedelta(days=30)
    expiring_soon = InventoryItem.objects.filter(
        status=InventoryItem.Status.AVAILABLE,
        expiry_date__isnull=False,
        expiry_date__lte=thirty_days_from_now
    ).order_by('expiry_date')[:5]  # แสดง 5 รายการ
    
    # ข้อมูลการตรวจนับล่าสุด
    recent_stock_counts = StockCount.objects.order_by('-count_date')[:3]  # 3 รายการล่าสุด
    
    # สินค้าเสียหายที่ยังไม่ได้ดำเนินการ
    pending_damaged_items = DamagedItem.objects.filter(
        status=DamagedItem.Status.PENDING
    ).order_by('-damage_date')[:5]  # แสดง 5 รายการ
    
    # ตำแหน่งจัดเก็บและจำนวนสินค้าในแต่ละตำแหน่ง
    locations = Location.objects.annotate(
        item_count=Count('inventoryitem', filter=Q(inventoryitem__status=InventoryItem.Status.AVAILABLE))
    ).order_by('-item_count')[:5]  # แสดง 5 ตำแหน่งที่มีสินค้ามากที่สุด
    
    context = {
        'inventory_stats': inventory_stats,
        'low_stock_products': low_stock_products,
        'expiring_soon': expiring_soon,
        'recent_stock_counts': recent_stock_counts,
        'pending_damaged_items': pending_damaged_items,
        'locations': locations,
    }
    
    return render(request, 'inventory/dashboard.html', context)

# ============================================
#  Inventory Item Views - จะพัฒนาเพิ่มเติมภายหลัง
# ============================================

@login_required
def inventory_item_list(request):
    """แสดงรายการสินค้าในคลังทั้งหมด"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    location_filter = request.GET.get('location', '')
    
    # Start with all items
    items = InventoryItem.objects.all()
    
    # Apply filters if provided
    if search_query:
        items = items.filter(
            Q(serial_number__icontains=search_query) |
            Q(product__name__icontains=search_query) |
            Q(lot_number__icontains=search_query)
        )
    
    if status_filter:
        items = items.filter(status=status_filter)
        
    if location_filter:
        items = items.filter(location_id=location_filter)
    
    # Order by most recently created
    items = items.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(items, 20)  # Show 20 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all locations for the filter dropdown
    locations = Location.objects.filter(is_active=True).order_by('location_name')
    
    context = {
        'page_obj': page_obj,
        'items': page_obj,  # Keep backward compatibility
        'search_query': search_query,
        'status_filter': status_filter,
        'location_filter': location_filter,
        'locations': locations,
        'status_choices': InventoryItem.Status.choices
    }
    
    return render(request, 'inventory/item_list.html', context)

@login_required
def inventory_item_detail(request, serial_number):
    """แสดงรายละเอียดของสินค้าในคลัง"""
    item = get_object_or_404(InventoryItem, serial_number=serial_number)
    
    # Get location history for this item
    location_history = item.location_history.all().order_by('-move_date')
    
    # Check if item is damaged
    is_damaged = hasattr(item, 'damage_record')
    
    context = {
        'item': item,
        'location_history': location_history,
        'is_damaged': is_damaged
    }
    
    return render(request, 'inventory/item_detail.html', context)

@login_required
def inventory_item_create(request):
    """เพิ่มสินค้าเข้าคลัง (manual)"""
    # Get all products and locations for the form
    products = Product.objects.all().order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('location_code')
    
    if request.method == 'POST':
        product_id = request.POST.get('product')
        location_id = request.POST.get('location')
        lot_number = request.POST.get('lot_number', '')
        expiry_date = request.POST.get('expiry_date') or None
        
        if product_id and location_id:
            try:
                product = Product.objects.get(id=product_id)
                location = Location.objects.get(id=location_id)
                
                # Create new inventory item
                item = InventoryItem.objects.create(
                    product=product,
                    location=location,
                    lot_number=lot_number,
                    expiry_date=expiry_date,
                    status=InventoryItem.Status.AVAILABLE,
                    created_by=request.user
                )
                
                messages.success(request, f'เพิ่มสินค้า {product.name} เข้าคลังเรียบร้อยแล้ว (S/N: {item.serial_number})')
                return redirect('inventory:item_detail', serial_number=item.serial_number)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    context = {
        'products': products,
        'locations': locations
    }
    
    return render(request, 'inventory/item_form.html', context)

# ============================================
#  Location Views - จะพัฒนาเพิ่มเติมภายหลัง
# ============================================

@login_required
def location_list(request):
    """แสดงรายการตำแหน่งจัดเก็บทั้งหมด"""
    # Get search parameter
    search_query = request.GET.get('search', '')
    
    # Filter locations
    if search_query:
        locations = Location.objects.filter(
            Q(location_name__icontains=search_query) |
            Q(location_code__icontains=search_query)
        )
    else:
        locations = Location.objects.all()
    
    # Add item count to each location
    locations = locations.annotate(
        total_items=Count('inventoryitem'),
        available_items=Count('inventoryitem', filter=Q(inventoryitem__status=InventoryItem.Status.AVAILABLE))
    ).order_by('location_code')
    
    context = {
        'locations': locations,
        'search_query': search_query
    }
    
    return render(request, 'inventory/location_list.html', context)

@login_required
def location_detail(request, location_id):
    """แสดงรายละเอียดของตำแหน่งจัดเก็บ"""
    location = get_object_or_404(Location, id=location_id)
    
    # Get items in this location with status filter
    status_filter = request.GET.get('status', '')
    
    # Start with all items in this location
    items = InventoryItem.objects.filter(location=location)
    
    # Apply status filter if provided
    if status_filter:
        items = items.filter(status=status_filter)
    
    # Get stats for this location
    status_counts = {
        'available': InventoryItem.objects.filter(location=location, status=InventoryItem.Status.AVAILABLE).count(),
        'reserved': InventoryItem.objects.filter(location=location, status=InventoryItem.Status.RESERVED).count(),
        'sold': InventoryItem.objects.filter(location=location, status=InventoryItem.Status.SOLD).count(),
        'damaged': InventoryItem.objects.filter(location=location, status=InventoryItem.Status.DAMAGED).count(),
        'expired': InventoryItem.objects.filter(location=location, status=InventoryItem.Status.EXPIRED).count(),
        'total': InventoryItem.objects.filter(location=location).count(),
    }
    
    context = {
        'location': location,
        'items': items,
        'status_counts': status_counts,
        'status_filter': status_filter,
        'status_choices': InventoryItem.Status.choices
    }
    
    return render(request, 'inventory/location_detail.html', context)

@login_required
def location_create(request):
    """เพิ่มตำแหน่งจัดเก็บใหม่"""
    if request.method == 'POST':
        location_code = request.POST.get('location_code')
        location_name = request.POST.get('location_name')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        
        if location_code and location_name:
            try:
                # Check if location code already exists
                if Location.objects.filter(location_code=location_code).exists():
                    messages.error(request, f'รหัสตำแหน่ง {location_code} มีอยู่ในระบบแล้ว')
                else:
                    # Create new location
                    location = Location.objects.create(
                        location_code=location_code,
                        location_name=location_name,
                        description=description,
                        is_active=is_active
                    )
                    messages.success(request, f'เพิ่มตำแหน่งจัดเก็บ {location_name} เรียบร้อยแล้ว')
                    return redirect('inventory:location_detail', location_id=location.id)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    return render(request, 'inventory/location_form.html')

@login_required
def location_edit(request, location_id):
    """แก้ไขข้อมูลตำแหน่งจัดเก็บ"""
    location = get_object_or_404(Location, id=location_id)
    
    if request.method == 'POST':
        location_name = request.POST.get('location_name')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        
        if location_name:
            try:
                # Update location
                location.location_name = location_name
                location.description = description
                location.is_active = is_active
                location.save()
                
                messages.success(request, f'แก้ไขตำแหน่งจัดเก็บ {location_name} เรียบร้อยแล้ว')
                return redirect('inventory:location_detail', location_id=location.id)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    return render(request, 'inventory/location_form.html', {'location': location})

# ============================================
#  Move Items Views - จะพัฒนาเพิ่มเติมภายหลัง
# ============================================

@login_required
def move_items(request):
    """ย้ายสินค้าระหว่างตำแหน่งจัดเก็บ"""
    locations = Location.objects.filter(is_active=True).order_by('location_code')
    
    if request.method == 'POST':
        move_type = request.POST.get('move_type', 'single')
        to_location_id = request.POST.get('to_location')
        reason = request.POST.get('reason', '')
        
        if not to_location_id:
            messages.error(request, 'กรุณาเลือกตำแหน่งปลายทาง')
            return render(request, 'inventory/move_items.html', {'locations': locations})
            
        try:
            to_location = Location.objects.get(id=to_location_id)
            
            if move_type == 'single':
                # Process single item move
                serial_number = request.POST.get('serial_number')
                if not serial_number:
                    messages.error(request, 'กรุณาระบุ Serial Number ของสินค้าที่ต้องการย้าย')
                    return render(request, 'inventory/move_items.html', {'locations': locations})
                
                # Find item by serial number
                item = InventoryItem.objects.get(serial_number=serial_number)
                from_location = item.location
                
                # Verify that source and destination are different
                if from_location.id == to_location.id:
                    messages.error(request, 'ตำแหน่งต้นทางและปลายทางต้องไม่เหมือนกัน')
                    return render(request, 'inventory/move_items.html', {'locations': locations})
                
                # Create location history record
                LocationHistory.objects.create(
                    inventory_item=item,
                    from_location=from_location,
                    to_location=to_location,
                    move_date=timezone.now(),
                    reason=reason,
                    moved_by=request.user
                )
                
                # Update item location
                item.location = to_location
                item.save()
                
                messages.success(request, f'ย้ายสินค้า {item.product.name} (S/N: {serial_number}) จาก {from_location.location_name} ไปยัง {to_location.location_name} เรียบร้อยแล้ว')
                
            elif move_type == 'bulk':
                # Process bulk move
                from_location_id = request.POST.get('from_location')
                move_all = request.POST.get('move_all', 'off')
                item_serials = request.POST.getlist('item_serials', [])
                
                if not from_location_id:
                    messages.error(request, 'กรุณาเลือกตำแหน่งต้นทาง')
                    return render(request, 'inventory/move_items.html', {'locations': locations})
                    
                from_location = Location.objects.get(id=from_location_id)
                
                if from_location.id == to_location.id:
                    messages.error(request, 'ตำแหน่งต้นทางและปลายทางต้องไม่เหมือนกัน')
                    return render(request, 'inventory/move_items.html', {'locations': locations})
                
                # Determine which items to move
                if move_all == 'on':
                    # Move all items in the location
                    items_to_move = InventoryItem.objects.filter(location=from_location)
                else:
                    # Move only specific items
                    if not item_serials:
                        messages.error(request, 'กรุณาเลือกสินค้าที่ต้องการย้าย')
                        return render(request, 'inventory/move_items.html', {'locations': locations})
                        
                    items_to_move = InventoryItem.objects.filter(serial_number__in=item_serials, location=from_location)
                
                # Move each item
                moved_count = 0
                for item in items_to_move:
                    # Create location history record
                    LocationHistory.objects.create(
                        inventory_item=item,
                        from_location=from_location,
                        to_location=to_location,
                        move_date=timezone.now(),
                        reason=reason,
                        moved_by=request.user
                    )
                    
                    # Update item location
                    item.location = to_location
                    item.save()
                    moved_count += 1
                
                if moved_count > 0:
                    messages.success(request, f'ย้ายสินค้าจำนวน {moved_count} รายการ จาก {from_location.location_name} ไปยัง {to_location.location_name} เรียบร้อยแล้ว')
                else:
                    messages.warning(request, 'ไม่มีสินค้าที่ถูกย้าย')
            
            # Clear form by redirecting back
            return redirect('inventory:move_items')
                
        except InventoryItem.DoesNotExist:
            messages.error(request, f'ไม่พบสินค้าที่มี Serial Number ที่ระบุ')
        except Location.DoesNotExist:
            messages.error(request, 'ตำแหน่งที่เลือกไม่ถูกต้อง')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    context = {
        'locations': locations
    }
    
    return render(request, 'inventory/move_items.html', context)

# ============================================
#  Stock Count Views - จะพัฒนาเพิ่มเติมภายหลัง
# ============================================

@login_required
def stock_count_list(request):
    """แสดงรายการตรวจนับสต็อก"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    location_filter = request.GET.get('location', '')
    
    # Start with all stock counts
    stock_counts = StockCount.objects.all()
    
    # Apply filters if provided
    if status_filter:
        stock_counts = stock_counts.filter(status=status_filter)
    
    if location_filter:
        stock_counts = stock_counts.filter(location_id=location_filter)
    
    # Order by most recent
    stock_counts = stock_counts.order_by('-count_date')
    
    # Get all locations for filter dropdown
    locations = Location.objects.filter(is_active=True).order_by('location_name')
    
    context = {
        'stock_counts': stock_counts,
        'status_filter': status_filter,
        'location_filter': location_filter,
        'locations': locations,
        'status_choices': StockCount.Status.choices
    }
    
    return render(request, 'inventory/stock_count_list.html', context)

@login_required
def stock_count_detail(request, count_id):
    """แสดงรายละเอียดของการตรวจนับสต็อก"""
    stock_count = get_object_or_404(StockCount, id=count_id)
    
    # Get all items in this count
    count_items = StockCountItem.objects.filter(stock_count=stock_count)
    
    # Calculate summary statistics
    found_count = count_items.filter(status=StockCountItem.Status.FOUND).count()
    missing_count = count_items.filter(status=StockCountItem.Status.MISSING).count()
    extra_count = count_items.filter(status=StockCountItem.Status.EXTRA).count()
    
    found_items = count_items.filter(status=StockCountItem.Status.FOUND)
    missing_items = count_items.filter(status=StockCountItem.Status.MISSING)
    extra_items = count_items.filter(status=StockCountItem.Status.EXTRA)
    
    context = {
        'stock_count': stock_count,
        'found_items': found_items,
        'missing_items': missing_items,
        'extra_items': extra_items,
        'found_count': found_count,
        'missing_count': missing_count,
        'extra_count': extra_count
    }
    
    return render(request, 'inventory/stock_count_detail.html', context)

@login_required
def stock_count_create(request):
    """สร้างการตรวจนับสต็อกใหม่"""
    # Get all active locations for the form
    locations = Location.objects.filter(is_active=True).order_by('location_code')
    
    if request.method == 'POST':
        # Basic form validation - to be expanded later
        location_id = request.POST.get('location')
        count_date = request.POST.get('count_date')
        note = request.POST.get('note', '')
        
        if location_id and count_date:
            try:
                location = Location.objects.get(id=location_id)
                # Create new stock count
                stock_count = StockCount.objects.create(
                    location=location,
                    count_date=count_date,
                    status=StockCount.Status.IN_PROGRESS,
                    counted_by=request.user,
                    note=note
                )
                messages.success(request, f'สร้างการตรวจนับสต็อกที่ {location.location_name} เรียบร้อยแล้ว')
                return redirect('inventory:stock_count_detail', count_id=stock_count.id)
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    return render(request, 'inventory/stock_count_form.html', {'locations': locations})

# ============================================
#  Damaged Item Views - จะพัฒนาเพิ่มเติมภายหลัง
# ============================================

@login_required
def damaged_item_list(request):
    """แสดงรายการสินค้าเสียหาย"""
    # Get query parameters for filtering
    search_query = request.GET.get('search', '')
    selected_status = request.GET.get('status', '')
    
    # Start with all items
    damaged_items = DamagedItem.objects.all()
    
    # Apply filters if provided
    if search_query:
        damaged_items = damaged_items.filter(
            Q(inventory_item__serial_number__icontains=search_query) |
            Q(inventory_item__product__name__icontains=search_query)
        )
    
    if selected_status:
        damaged_items = damaged_items.filter(status=selected_status)
    
    # Order by most recent damage date
    damaged_items = damaged_items.order_by('-damage_date')
    
    context = {
        'damaged_items': damaged_items,
        'search_query': search_query,
        'selected_status': selected_status
    }
    
    return render(request, 'inventory/damaged_item_list.html', context)

@login_required
def damaged_item_detail(request, item_id):
    """แสดงรายละเอียดของสินค้าเสียหาย"""
    damaged_item = get_object_or_404(DamagedItem, inventory_item_id=item_id)
    
    # Handle form submission for updating damage status
    if request.method == 'POST':
        action = request.POST.get('action')
        repair_cost = request.POST.get('repair_cost', 0)
        action_note = request.POST.get('action_note', '')
        
        if action in ['repaired', 'written_off']:
            try:
                # Update damaged item status
                damaged_item.status = action
                damaged_item.repair_cost = repair_cost
                damaged_item.action_date = timezone.now().date()
                damaged_item.action_note = action_note
                damaged_item.save()
                
                # Update inventory item status
                if action == 'repaired':
                    damaged_item.inventory_item.status = InventoryItem.Status.AVAILABLE
                    messages.success(request, 'บันทึกการซ่อมแซมเรียบร้อยแล้ว')
                else:  # written_off
                    damaged_item.inventory_item.status = InventoryItem.Status.DAMAGED  # Keep as damaged for record
                    messages.success(request, 'บันทึกการตัดจำหน่ายเรียบร้อยแล้ว')
                
                damaged_item.inventory_item.save()
                
                return redirect('inventory:damaged_item_list')
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return render(request, 'inventory/damaged_item_detail.html', {'damaged_item': damaged_item})

@login_required
def report_damaged_item(request):
    """รายงานสินค้าเสียหาย"""
    if request.method == 'POST':
        serial_number = request.POST.get('serial_number')
        damage_date = request.POST.get('damage_date')
        damage_description = request.POST.get('damage_description')
        
        if serial_number and damage_date and damage_description:
            try:
                # Find the inventory item
                inventory_item = get_object_or_404(InventoryItem, serial_number=serial_number)
                
                # Check if this item is already reported as damaged
                if DamagedItem.objects.filter(inventory_item=inventory_item).exists():
                    messages.error(request, 'สินค้านี้ถูกรายงานว่าเสียหายไปแล้ว')
                    return redirect('inventory:damaged_item_list')
                
                # Update the inventory item status
                inventory_item.status = InventoryItem.Status.DAMAGED
                inventory_item.save()
                
                # Create damaged item record
                damaged_item = DamagedItem.objects.create(
                    inventory_item=inventory_item,
                    damage_date=damage_date,
                    damage_description=damage_description,
                    status=DamagedItem.Status.PENDING,
                    created_by=request.user
                )
                
                messages.success(request, f'รายงานสินค้าเสียหาย {inventory_item.product.name} (S/N: {serial_number}) เรียบร้อยแล้ว')
                return redirect('inventory:damaged_item_detail', item_id=inventory_item.id)
                
            except InventoryItem.DoesNotExist:
                messages.error(request, f'ไม่พบสินค้าที่มี Serial Number: {serial_number}')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    
    return render(request, 'inventory/report_damaged.html')

# ============================================
#  API Views for AJAX
# ============================================

@login_required
def inventory_item_api(request, serial_number):
    """API endpoint to get item details by serial number"""
    try:
        item = InventoryItem.objects.get(serial_number=serial_number)
        data = {
            'id': item.id,
            'serial_number': item.serial_number,
            'product_name': item.product.name,
            'product_id': item.product.id,
            'location_name': f"{item.location.location_code} - {item.location.location_name}",
            'location_id': item.location.id,
            'status': item.status,
            'status_display': item.get_status_display(),
            'expiry_date': item.expiry_date.strftime('%Y-%m-%d') if item.expiry_date else None,
            'lot_number': item.lot_number or ''
        }
        return JsonResponse(data)
    except InventoryItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)

# ============================================
#  Inventory Report Views
# ============================================

@login_required
def inventory_report(request):
    """หน้ารายงานและการวิเคราะห์คลังสินค้า"""
    
    # ================== สถิติภาพรวม ==================
    total_items = InventoryItem.objects.count()
    total_value = InventoryItem.objects.filter(
        status=InventoryItem.Status.AVAILABLE
    ).aggregate(
        total=Sum(F('product__price_a'))
    )['total'] or Decimal('0')
    
    # สถิติตามสถานะ
    status_stats = {}
    for status_choice in InventoryItem.Status.choices:
        status_code = status_choice[0]
        status_count = InventoryItem.objects.filter(status=status_code).count()
        percentage = (status_count / total_items * 100) if total_items > 0 else 0
        status_stats[status_code] = {
            'count': status_count,
            'percentage': round(percentage, 1),
            'display': status_choice[1]
        }
    
    # ================== วิเคราะห์สินค้า ==================
    # สินค้าที่ต้องสั่งซื้อเพิ่ม
    low_stock_analysis = Product.objects.filter(
        reorder_point__gt=0
    ).annotate(
        available_count=Count(
            'inventoryitem', 
            filter=Q(inventoryitem__status=InventoryItem.Status.AVAILABLE)
        ),
        shortage=F('reorder_point') - F('available_count')
    ).filter(
        available_count__lt=F('reorder_point')
    ).order_by('-shortage')
    
    # สินค้าใกล้หมดอายุ (3 ช่วง: 7, 30, 90 วัน)
    today = timezone.now().date()
    expiry_analysis = {
        'week': InventoryItem.objects.filter(
            status=InventoryItem.Status.AVAILABLE,
            expiry_date__isnull=False,
            expiry_date__lte=today + timedelta(days=7),
            expiry_date__gte=today
        ).count(),
        'month': InventoryItem.objects.filter(
            status=InventoryItem.Status.AVAILABLE,
            expiry_date__isnull=False,
            expiry_date__lte=today + timedelta(days=30),
            expiry_date__gt=today + timedelta(days=7)
        ).count(),
        'quarter': InventoryItem.objects.filter(
            status=InventoryItem.Status.AVAILABLE,
            expiry_date__isnull=False,
            expiry_date__lte=today + timedelta(days=90),
            expiry_date__gt=today + timedelta(days=30)
        ).count(),
    }
    
    # สินค้าเสียหายรายเดือน (6 เดือนล่าสุด)
    six_months_ago = today - timedelta(days=180)
    damaged_trend = DamagedItem.objects.filter(
        damage_date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('damage_date')
    ).values('month').annotate(
        count=Count('inventory_item')
    ).order_by('month')
    
    # ================== วิเคราะห์ตำแหน่งจัดเก็บ ==================
    location_analysis = Location.objects.filter(
        is_active=True
    ).annotate(
        total_items=Count('inventoryitem'),
        available_items=Count(
            'inventoryitem',
            filter=Q(inventoryitem__status=InventoryItem.Status.AVAILABLE)
        ),
        total_value=Sum(
            F('inventoryitem__product__price_a'),
            filter=Q(inventoryitem__status=InventoryItem.Status.AVAILABLE)
        )
    ).order_by('-total_value')
    
    # Top 10 products ที่มีมูลค่าสูงสุดในคลัง
    top_value_products = Product.objects.annotate(
        available_count=Count(
            'inventoryitem',
            filter=Q(inventoryitem__status=InventoryItem.Status.AVAILABLE)
        ),
        total_value=F('available_count') * F('price_a')
    ).filter(
        available_count__gt=0
    ).order_by('-total_value')[:10]
    
    # ================== การตรวจนับล่าสุด ==================
    recent_stock_counts = StockCount.objects.select_related(
        'location', 'counted_by'
    ).order_by('-count_date')[:5]
    
    # สถิติการตรวจนับ
    stock_count_stats = {
        'total': StockCount.objects.count(),
        'completed': StockCount.objects.filter(status=StockCount.Status.COMPLETED).count(),
        'in_progress': StockCount.objects.filter(status=StockCount.Status.IN_PROGRESS).count(),
        'this_month': StockCount.objects.filter(
            count_date__month=today.month,
            count_date__year=today.year
        ).count()
    }
    
    # ================== Alert และ Warning ==================
    alerts = []
    
    # สินค้าใกล้หมดอายุ 7 วัน
    if expiry_analysis['week'] > 0:
        alerts.append({
            'type': 'danger',
            'message': f'มีสินค้า {expiry_analysis["week"]} รายการ ที่จะหมดอายุภายใน 7 วัน'
        })
    
    # สินค้าต้องสั่งซื้อเพิ่ม
    low_stock_count = low_stock_analysis.count()
    if low_stock_count > 0:
        alerts.append({
            'type': 'warning',
            'message': f'มีสินค้า {low_stock_count} รายการ ที่ต้องสั่งซื้อเพิ่ม'
        })
    
    context = {
        # สถิติหลัก
        'total_items': total_items,
        'total_value': total_value,
        'status_stats': status_stats,
        
        # การวิเคราะห์
        'low_stock_analysis': low_stock_analysis[:10],  # แสดง 10 อันดับแรก
        'expiry_analysis': expiry_analysis,
        'damaged_trend': list(damaged_trend),
        'location_analysis': location_analysis[:10],  # แสดง 10 อันดับแรก
        'top_value_products': top_value_products,
        
        # การตรวจนับ
        'recent_stock_counts': recent_stock_counts,
        'stock_count_stats': stock_count_stats,
        
        # Alert
        'alerts': alerts,
    }
    
    return render(request, 'inventory/report.html', context)

# ============================================
#  Stock Count Process Views - การตรวจนับสต็อก
# ============================================

@login_required
def stock_count_scan(request, count_id):
    """หน้าสำหรับสแกนและตรวจนับสินค้า"""
    stock_count = get_object_or_404(StockCount, id=count_id)
    
    # ตรวจสอบว่ากำลังอยู่ในขั้นตอนการตรวจนับหรือไม่
    if stock_count.status != StockCount.Status.IN_PROGRESS:
        messages.error(request, 'การตรวจนับนี้ไม่อยู่ในสถานะกำลังดำเนินการ ไม่สามารถทำการนับได้')
        return redirect('inventory:stock_count_detail', count_id=count_id)
    
    # รับค่าจากการสแกน
    if request.method == 'POST':
        scanned_serial = request.POST.get('scanned_serial', '')
        note = request.POST.get('note', '')
        
        if scanned_serial:
            # ค้นหาสินค้าในระบบ
            try:
                inventory_item = InventoryItem.objects.get(serial_number=scanned_serial)
                
                # ตรวจสอบว่าสินค้านี้อยู่ในตำแหน่งที่กำลังตรวจนับหรือไม่
                if inventory_item.location_id != stock_count.location_id:
                    messages.warning(request, 
                        f'สินค้า {inventory_item.product.name} (S/N: {scanned_serial}) '
                        f'ไม่ได้อยู่ในตำแหน่ง {stock_count.location.location_name} ตามระบบ'
                    )
                
                # เช็คว่าเคยมีในรายการตรวจนับหรือยัง
                existing_item = StockCountItem.objects.filter(
                    stock_count=stock_count,
                    inventory_item=inventory_item
                ).first()
                
                if existing_item:
                    messages.info(request, 
                        f'สินค้า {inventory_item.product.name} (S/N: {scanned_serial}) '
                        f'ถูกตรวจนับไปแล้ว (สถานะ: {existing_item.get_status_display()})'
                    )
                else:
                    # เพิ่มสินค้าในรายการตรวจนับ
                    stock_count_item = StockCountItem.objects.create(
                        stock_count=stock_count,
                        inventory_item=inventory_item,
                        status=StockCountItem.Status.FOUND,
                        note=note
                    )
                    messages.success(request, 
                        f'ตรวจนับสินค้า {inventory_item.product.name} (S/N: {scanned_serial}) สำเร็จ'
                    )
            except InventoryItem.DoesNotExist:
                # สินค้าไม่มีในระบบ - ให้ผู้ใช้ระบุว่าเป็นสินค้าเกิน
                messages.warning(request, 
                    f'ไม่พบสินค้าหมายเลข {scanned_serial} ในระบบ กรุณาระบุข้อมูลเพิ่มเติมเพื่อบันทึกเป็นสินค้าเกิน'
                )
                return redirect('inventory:stock_count_add_extra', count_id=count_id, serial=scanned_serial)
    
    # คำนวณสถิติการนับ
    count_items = StockCountItem.objects.filter(stock_count=stock_count)
    found_items = count_items.filter(status=StockCountItem.Status.FOUND)
    
    # ดึงรายการที่สแกนล่าสุด (10 รายการ) สำหรับแสดงในตาราง
    recent_items = StockCountItem.objects.filter(
        stock_count=stock_count,
        status=StockCountItem.Status.FOUND
    ).order_by('-id')[:10]  # เรียงลำดับตาม id ล่าสุด
    
    # สินค้าที่อยู่ในระบบแต่ยังไม่ได้ตรวจนับ (missing)
    inventory_items_in_location = InventoryItem.objects.filter(
        location=stock_count.location,
        status=InventoryItem.Status.AVAILABLE
    )
    scanned_item_ids = found_items.values_list('inventory_item_id', flat=True)
    missing_items = inventory_items_in_location.exclude(id__in=scanned_item_ids)
    
    context = {
        'stock_count': stock_count,
        'found_items': found_items,
        'missing_items': missing_items,
        'missing_count': missing_items.count(),
        'found_count': found_items.count(),
        'recent_items': recent_items,  # เพิ่มรายการที่สแกนล่าสุดเข้าไปใน context
    }
    
    return render(request, 'inventory/stock_count_scan.html', context)
    
    return render(request, 'inventory/stock_count_scan.html', context)

@login_required
def stock_count_add_extra(request, count_id):
    """หน้าสำหรับเพิ่มสินค้าเกิน (สินค้าที่พบแต่ไม่มีในระบบ)"""
    stock_count = get_object_or_404(StockCount, id=count_id)
    
    # ตรวจสอบว่ากำลังอยู่ในขั้นตอนการตรวจนับหรือไม่
    if stock_count.status != StockCount.Status.IN_PROGRESS:
        messages.error(request, 'การตรวจนับนี้ไม่อยู่ในสถานะกำลังดำเนินการ ไม่สามารถเพิ่มสินค้าเกินได้')
        return redirect('inventory:stock_count_detail', count_id=count_id)
    
    # รับ serial number จาก URL parameter
    serial = request.GET.get('serial', '')
    
    if request.method == 'POST':
        product_id = request.POST.get('product')
        product_name = request.POST.get('product_name')
        counted_serial = request.POST.get('counted_serial', serial)
        note = request.POST.get('note', '')
        
        # กรณีเลือกสินค้าจาก dropdown
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                
                # เพิ่มสินค้าเกินในรายการตรวจนับ
                stock_count_item = StockCountItem.objects.create(
                    stock_count=stock_count,
                    product=product,
                    status=StockCountItem.Status.EXTRA,
                    counted_serial_number=counted_serial,
                    note=note
                )
                
                messages.success(request, f'เพิ่มสินค้าเกิน {product.name} เรียบร้อยแล้ว')
                return redirect('inventory:stock_count_detail', count_id=count_id)
            except Product.DoesNotExist:
                messages.error(request, 'ไม่พบสินค้าที่เลือกในระบบ')
        # กรณีกรอกชื่อสินค้าใหม่
        elif product_name:
            # สร้างสินค้าใหม่ในระบบ (หรือใช้เฉพาะในการตรวจนับโดยไม่บันทึกเข้าระบบหลัก)
            # ตัวอย่างนี้จะบันทึกเฉพาะในการตรวจนับ
            stock_count_item = StockCountItem.objects.create(
                stock_count=stock_count,
                status=StockCountItem.Status.EXTRA,
                counted_serial_number=counted_serial,
                note=f"สินค้าไม่มีในระบบ: {product_name}\n{note}"
            )
            
            messages.success(request, f'เพิ่มสินค้าเกิน "{product_name}" เรียบร้อยแล้ว')
            return redirect('inventory:stock_count_detail', count_id=count_id)
        else:
            messages.error(request, 'กรุณาเลือกสินค้าหรือกรอกชื่อสินค้า')
    
    # ดึงข้อมูลสินค้าทั้งหมดสำหรับแสดงในฟอร์ม
    products = Product.objects.all().order_by('name')
    
    context = {
        'stock_count': stock_count,
        'serial': serial,
        'products': products
    }
    
    return render(request, 'inventory/stock_count_add_extra.html', context)

@login_required
def stock_count_complete(request, count_id):
    """จบการตรวจนับและทำการประมวลผล"""
    stock_count = get_object_or_404(StockCount, id=count_id)
    
    # ตรวจสอบว่ากำลังอยู่ในขั้นตอนการตรวจนับหรือไม่
    if stock_count.status != StockCount.Status.IN_PROGRESS:
        messages.error(request, 'การตรวจนับนี้ไม่อยู่ในสถานะกำลังดำเนินการ ไม่สามารถเสร็จสิ้นการนับได้')
        return redirect('inventory:stock_count_detail', count_id=count_id)
    
    if request.method == 'POST':
        # ดึงข้อมูลสินค้าในตำแหน่งนี้ทั้งหมด
        inventory_items = InventoryItem.objects.filter(
            location=stock_count.location,
            status=InventoryItem.Status.AVAILABLE
        )
        
        # ดึงข้อมูลสินค้าที่ตรวจนับพบแล้ว
        found_items = StockCountItem.objects.filter(
            stock_count=stock_count,
            status=StockCountItem.Status.FOUND
        ).values_list('inventory_item_id', flat=True)
        
        # สินค้าที่ไม่พบในการตรวจนับ - บันทึกเป็น missing
        for item in inventory_items:
            if item.id not in found_items:
                StockCountItem.objects.create(
                    stock_count=stock_count,
                    inventory_item=item,
                    status=StockCountItem.Status.MISSING,
                    note="ไม่พบในการตรวจนับ"
                )
        
        # อัปเดตสถานะการตรวจนับเป็น "เสร็จสิ้น"
        stock_count.status = StockCount.Status.COMPLETED
        stock_count.save()
        
        messages.success(request, 'เสร็จสิ้นการตรวจนับสต็อกเรียบร้อยแล้ว')
        return redirect('inventory:stock_count_detail', count_id=count_id)
    
    # คำนวณสถิติการนับสำหรับหน้ายืนยัน
    count_items = StockCountItem.objects.filter(stock_count=stock_count)
    found_count = count_items.filter(status=StockCountItem.Status.FOUND).count()
    extra_count = count_items.filter(status=StockCountItem.Status.EXTRA).count()
    
    # สินค้าที่อยู่ในระบบแต่ยังไม่ได้ตรวจนับ (จะถูกบันทึกเป็น missing)
    inventory_items_in_location = InventoryItem.objects.filter(
        location=stock_count.location,
        status=InventoryItem.Status.AVAILABLE
    )
    scanned_item_ids = count_items.filter(status=StockCountItem.Status.FOUND).values_list('inventory_item_id', flat=True)
    missing_count = inventory_items_in_location.exclude(id__in=scanned_item_ids).count()
    
    context = {
        'stock_count': stock_count,
        'found_count': found_count,
        'missing_count': missing_count,
        'extra_count': extra_count
    }
    
    return render(request, 'inventory/stock_count_complete.html', context)

@login_required
def stock_count_mark_item(request, count_id, item_id):
    """ปรับเปลี่ยนสถานะของสินค้าในการตรวจนับ (found/missing)"""
    stock_count = get_object_or_404(StockCount, id=count_id)
    inventory_item = get_object_or_404(InventoryItem, id=item_id)
    
    # ตรวจสอบว่ากำลังอยู่ในขั้นตอนการตรวจนับหรือไม่
    if stock_count.status != StockCount.Status.IN_PROGRESS:
        messages.error(request, 'การตรวจนับนี้ไม่อยู่ในสถานะกำลังดำเนินการ ไม่สามารถแก้ไขสถานะสินค้าได้')
        return redirect('inventory:stock_count_detail', count_id=count_id)
    
    action = request.POST.get('action')
    note = request.POST.get('note', '')
    
    if request.method == 'POST' and action in ['found', 'missing']:
        # ตรวจสอบว่ามีการบันทึกสินค้านี้ในการตรวจนับหรือยัง
        stock_count_item, created = StockCountItem.objects.get_or_create(
            stock_count=stock_count,
            inventory_item=inventory_item,
            defaults={
                'status': action,
                'note': note
            }
        )
        
        # ถ้ามีอยู่แล้ว อัปเดตสถานะ
        if not created:
            stock_count_item.status = action
            stock_count_item.note = note
            stock_count_item.save()
        
        status_text = "พบ" if action == "found" else "ไม่พบ"
        messages.success(request, f'บันทึกสถานะสินค้า {inventory_item.product.name} (S/N: {inventory_item.serial_number}) เป็น "{status_text}" เรียบร้อย')
    
    # กลับไปยังหน้าจอการสแกน
    return redirect('inventory:stock_count_scan', count_id=count_id)
