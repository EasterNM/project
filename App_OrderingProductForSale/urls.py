from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Dashboard
    path('', views.order_dashboard, name='dashboard'),
    path('dashboard/', views.order_dashboard, name='dashboard'),
    
    # Order Management
    path('new/', views.create_order, name='create_order'),
    path('list/', views.order_list, name='order_list'),
    path('detail/<str:order_id>/', views.order_detail, name='order_detail'),
    path('picking/<str:order_id>/', views.order_picking, name='order_picking'),
    
    # Invoice Management
    path('invoice/<str:order_id>/', views.create_invoice, name='create_invoice'),
    path('invoice/detail/<str:invoice_number>/', views.invoice_detail, name='invoice_detail'),
    
    # Reports & Export
    path('reports/', views.order_reports, name='reports'),
    path('export/orders/', views.export_orders, name='export_orders'),
    path('export/invoices/', views.export_invoices, name='export_invoices'),
]
