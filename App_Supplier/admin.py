from django.contrib import admin
from .models import Supplier, ContactHistory

class ContactHistoryInline(admin.TabularInline):
    model = ContactHistory
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('contact_date', 'contact_type', 'notes', 'created_by', 'created_at', 'updated_at')

class SupplierAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'supplier_code', 'contact_name', 'phone_number', 'email', 'category', 'status')
    list_filter = ('status', 'category', 'city', 'state', 'country')
    search_fields = ('company_name', 'supplier_code', 'contact_name', 'email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ContactHistoryInline]
    
    fieldsets = (
        ('ข้อมูลทั่วไป', {
            'fields': ('company_name', 'supplier_code', 'category', 'status')
        }),
        ('ข้อมูลผู้ติดต่อ', {
            'fields': ('contact_name', 'contact_title', 'email', 'phone_number', 'fax_number', 'website')
        }),
        ('ข้อมูลที่อยู่', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        ('ข้อมูลการเงิน', {
            'fields': ('tax_id', 'bank_name', 'bank_account_number', 'payment_terms', 'credit_limit')
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(Supplier, SupplierAdmin)
admin.site.register(ContactHistory)
