from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # หน้าหลักคลังสินค้า
    path('', views.inventory_dashboard, name='dashboard'),
    
    # รายงานสต็อกสินค้า
    path('report/', views.inventory_report, name='report'),
    
    # การจัดการสินค้าในคลัง
    path('items/', views.inventory_item_list, name='item_list'),
    path('items/create/', views.inventory_item_create, name='item_create'),
    path('items/<str:serial_number>/', views.inventory_item_detail, name='item_detail'),
    
    # การจัดการตำแหน่งจัดเก็บ
    path('locations/', views.location_list, name='location_list'),
    path('locations/create/', views.location_create, name='location_create'),
    path('locations/<int:location_id>/', views.location_detail, name='location_detail'),
    path('locations/<int:location_id>/edit/', views.location_edit, name='location_edit'),
    
    # การย้ายสินค้า
    path('move/', views.move_items, name='move_items'),
    
    # การตรวจนับสต็อก
    path('stock-count/', views.stock_count_list, name='stock_count_list'),
    path('stock-count/create/', views.stock_count_create, name='stock_count_create'),
    path('stock-count/<int:count_id>/', views.stock_count_detail, name='stock_count_detail'),
    path('stock-count/<int:count_id>/scan/', views.stock_count_scan, name='stock_count_scan'),
    path('stock-count/<int:count_id>/add-extra/', views.stock_count_add_extra, name='stock_count_add_extra'),
    path('stock-count/<int:count_id>/complete/', views.stock_count_complete, name='stock_count_complete'),
    path('stock-count/<int:count_id>/mark-item/', views.stock_count_mark_item, name='stock_count_mark_item'),
    
    # การจัดการสินค้าเสียหาย
    path('damaged/', views.damaged_item_list, name='damaged_item_list'),
    path('damaged/report/', views.report_damaged_item, name='report_damaged'),
    path('damaged/<int:item_id>/', views.damaged_item_detail, name='damaged_item_detail'),
    
    # API endpoints
    path('api/items/<str:serial_number>/', views.inventory_item_api, name='item_api'),
]
