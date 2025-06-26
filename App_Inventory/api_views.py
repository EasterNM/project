from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import InventoryItem

def inventory_item_api(request, serial_number):
    """API endpoint for retrieving inventory item details by serial number"""
    item = get_object_or_404(InventoryItem, serial_number=serial_number)
    
    # Return basic information needed for the move items form
    data = {
        'serial_number': item.serial_number,
        'product_name': item.product.name,
        'location_id': item.location.id,
        'location_name': item.location.location_name,
        'status': item.status
    }
    
    return JsonResponse(data)
