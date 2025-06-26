from django.urls import path
from . import views

app_name = 'purchase'

urlpatterns = [
    # Dashboard
    path('', views.purchase_dashboard, name='dashboard'),
    
    # Purchase Requisition (PR) URLs
    path('requisition/', views.requisition_list, name='requisition_list'),
    path('requisition/create/', views.requisition_create, name='requisition_create'),
    path('requisition/<str:pr_number>/', views.requisition_detail, name='requisition_detail'),
    path('requisition/<str:pr_number>/edit/', views.requisition_edit, name='requisition_edit'),
    path('requisition/<str:pr_number>/approve/', views.requisition_approve, name='requisition_approve'),
    path('requisition/<str:pr_number>/cancel/', views.requisition_cancel, name='requisition_cancel'),
    
    # Purchase Order (PO) URLs
    path('order/', views.order_list, name='order_list'),
    path('order/create/', views.order_create, name='order_create'),
    path('order/create-from-pr/<str:pr_number>/', views.order_create_from_pr, name='order_create_from_pr'),
    path('order/<str:po_number>/', views.order_detail, name='order_detail'),
    path('order/<str:po_number>/edit/', views.order_edit, name='order_edit'),
    path('order/<str:po_number>/approve/', views.order_approve, name='order_approve'),
    path('order/<str:po_number>/cancel/', views.order_cancel, name='order_cancel'),
    
    # Goods Receipt URLs
    path('receipt/', views.receipt_list, name='receipt_list'),
    path('receipt/create/<str:po_number>/', views.receipt_create, name='receipt_create'),
    path('receipt/<int:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    
    # Reports & Exports
    path('reports/', views.purchase_reports, name='reports'),
    path('export/purchase-orders/', views.export_purchase_orders, name='export_purchase_orders'),
    path('export/purchase-requisitions/', views.export_purchase_requisitions, name='export_purchase_requisitions'),
    
    # API Endpoints
    path('api/product-prices/<int:supplier_id>/', views.get_product_prices, name='get_product_prices'),
]
