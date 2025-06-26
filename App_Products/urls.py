from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Dashboard and Reports
    path('dashboard/', views.product_dashboard, name='dashboard'),
    path('reports/', views.product_reports, name='reports'),
    path('export/', views.export_products, name='export_products'),
    
    # Product URLs
    path('', views.product_list, name='product_list'),
    path('add/', views.product_add, name='product_add'),
    path('create/', views.product_create, name='product_create'),
    path('<int:product_id>/', views.product_detail, name='product_detail'),
    path('<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('<int:product_id>/update/', views.product_update, name='product_update'),
    
    # Category URLs
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/', views.category_detail, name='category_detail'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:category_id>/update/', views.category_update, name='category_update'),
    
    # Brand URLs
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/add/', views.brand_add, name='brand_add'),
    path('brands/create/', views.brand_create, name='brand_create'),
    path('brands/<int:brand_id>/', views.brand_detail, name='brand_detail'),
    path('brands/<int:brand_id>/edit/', views.brand_edit, name='brand_edit'),
    path('brands/<int:brand_id>/update/', views.brand_update, name='brand_update'),
    
    # Testing route (only for admins)
    path('test-sku-generation/', views.test_sku_generation, name='test_sku_generation'),
]
