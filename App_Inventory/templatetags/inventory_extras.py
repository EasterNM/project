from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        try:
            return value - arg
        except:
            return 0

@register.filter
def div(value, arg):
    """Divide the value by arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """Multiply the value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percent(value, total):
    """Calculate percentage."""
    try:
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def status_color(status):
    """Return CSS color class for status."""
    color_map = {
        'available': 'text-green-600',
        'reserved': 'text-yellow-600',
        'sold': 'text-blue-600',
        'damaged': 'text-red-600',
        'expired': 'text-red-700',
    }
    return color_map.get(status.lower(), 'text-gray-600')

@register.filter
def status_bg_color(status):
    """Return CSS background color class for status."""
    color_map = {
        'available': 'bg-green-100',
        'reserved': 'bg-yellow-100',
        'sold': 'bg-blue-100',
        'damaged': 'bg-red-100',
        'expired': 'bg-red-200',
    }
    return color_map.get(status.lower(), 'bg-gray-100')

@register.filter
def utilization_color(value):
    """Return CSS color class for utilization percentage."""
    try:
        val = float(value)
        if val > 100:
            return 'text-red-600'
        elif val > 80:
            return 'text-yellow-600'
        else:
            return 'text-green-600'
    except (ValueError, TypeError):
        return 'text-gray-600'

@register.filter
def format_currency(value):
    """Format number as currency."""
    try:
        return f"฿{float(value):,.2f}"
    except (ValueError, TypeError):
        return "฿0.00"

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary."""
    return dictionary.get(key, None)

@register.filter
def calculate_order_total(order_details):
    """Calculate total amount from order details."""
    try:
        total = sum(detail.subtotal for detail in order_details if detail.subtotal)
        return total
    except (ValueError, TypeError, AttributeError):
        return 0
