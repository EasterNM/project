from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Main dashboard
    path('', views.customer_dashboard, name='dashboard'),
    
    # Customer CRUD operations
    path('list/', views.customer_list, name='customer_list'),
    path('add/', views.customer_add, name='customer_add'),
    path('<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('<int:customer_id>/edit/', views.customer_edit, name='customer_edit'),
    
    # Contact history management
    path('<int:customer_id>/contact/', views.add_contact_history, name='add_contact_history'),
    path('<int:customer_id>/contact/<int:contact_id>/delete/', views.delete_contact_history, name='delete_contact_history'),
    
    # Reports and analytics
    path('reports/', views.customer_reports, name='customer_reports'),
    path('export/', views.export_customers, name='export_customers'),
]
