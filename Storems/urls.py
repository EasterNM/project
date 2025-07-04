"""
URL configuration for Storems project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import HttpResponse

# Views to handle PWA-related requests
def manifest_json(request):
    return HttpResponse('{}', content_type='application/json', status=200)

def serviceworker_js(request):
    return HttpResponse('// No service worker available', content_type='application/javascript', status=200)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('App_Accounts.urls')),
    path('', include('App_General.urls')),
    path('products/', include('App_Products.urls', namespace='products')),
    path('inventory/', include('App_Inventory.urls', namespace='inventory')),
    path('purchase/', include('App_Purchase.urls', namespace='purchase')),
    path('orders/', include('App_OrderingProductForSale.urls', namespace='orders')),
    path('customers/', include('App_Customer.urls', namespace='customers')),
    path('suppliers/', include('App_Supplier.urls', namespace='suppliers')),
    # Handle PWA-related requests to prevent 404 errors in logs
    path('manifest.json', manifest_json, name='manifest'),
    path('serviceworker.js', serviceworker_js, name='serviceworker'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
