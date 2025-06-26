from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    # Main dashboard
    path('', views.supplier_dashboard, name='dashboard'),
    
    # Supplier CRUD operations
    path('list/', views.supplier_list, name='supplier_list'),
    path('add/', views.supplier_add, name='supplier_add'),
    path('<int:supplier_id>/', views.supplier_detail, name='supplier_detail'),
    path('<int:supplier_id>/edit/', views.supplier_edit, name='supplier_edit'),
    
    # Contact history management
    path('<int:supplier_id>/contact/', views.add_contact_history, name='add_contact_history'),
    path('<int:supplier_id>/contact/<int:contact_id>/delete/', views.delete_contact_history, name='delete_contact_history'),
    
    # Reports and analytics
    path('reports/', views.supplier_reports, name='supplier_reports'),
    path('export/', views.export_suppliers, name='export_suppliers'),
]
