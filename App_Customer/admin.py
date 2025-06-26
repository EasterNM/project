from django.contrib import admin
from .models import Customer, CustomerContactHistory


class CustomerContactHistoryInline(admin.TabularInline):
    model = CustomerContactHistory
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('contact_type', 'contact_date', 'subject', 'description', 'contacted_by', 'created_at')


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_code', 'contact_name', 'phone_number', 'email', 'customer_type', 'status')
    list_filter = ('status', 'customer_type', 'city', 'state', 'country', 'price_tier')
    search_fields = ('name', 'customer_code', 'contact_name', 'email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CustomerContactHistoryInline]
    
    fieldsets = (
        ('ข้อมูลทั่วไป', {
            'fields': ('name', 'customer_code', 'customer_type', 'status')
        }),
        ('ข้อมูลผู้ติดต่อ', {
            'fields': ('contact_name', 'contact_title', 'email', 'phone_number', 'fax_number', 'website')
        }),
        ('ข้อมูลที่อยู่', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        ('ข้อมูลการเงิน', {
            'fields': ('tax_id', 'bank_name', 'bank_account_number', 'price_tier', 'credit_limit', 'payment_terms', 'credit_term')
        }),
        ('ข้อมูลเพิ่มเติม', {
            'fields': ('notes',)
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


admin.site.register(Customer, CustomerAdmin)
admin.site.register(CustomerContactHistory)
