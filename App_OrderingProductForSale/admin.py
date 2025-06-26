from django.contrib import admin
from .models import (
    OrderRequest, OrderDetail, PickingOrder, PickingDetail, 
    Invoice, OrderCounter, InvoiceCounter
)

class OrderDetailInline(admin.TabularInline):
    model = OrderDetail
    extra = 0
    fields = ('product', 'quantity', 'unit_price', 'subtotal')
    readonly_fields = ('unit_price', 'subtotal',)
    
class OrderRequestAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'customer', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_id', 'customer__name')
    readonly_fields = ('order_id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('ข้อมูลคำสั่งซื้อ', {
            'fields': ('order_id', 'customer', 'status', 'created_by')
        }),
        ('หมายเหตุ', {
            'fields': ('note',)
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrderDetailInline]

class PickingDetailInline(admin.TabularInline):
    model = PickingDetail
    extra = 0
    fields = ('order_detail', 'picked_items')

class PickingOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_request', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_request__order_id',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('ข้อมูลการจัดสินค้า', {
            'fields': ('order_request', 'status', 'picker')
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PickingDetailInline]

class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'invoice_type', 'order_request', 'issue_date', 'created_at')
    list_filter = ('invoice_type', 'issue_date', 'created_at')
    search_fields = ('invoice_number', 'order_request__order_id')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at', 'total_amount', 'subtotal', 'vat_amount', 'grand_total')
    
    fieldsets = (
        ('ข้อมูลใบแจ้งหนี้', {
            'fields': ('invoice_number', 'invoice_type', 'order_request')
        }),
        ('วันที่', {
            'fields': ('issue_date', 'due_date')
        }),
        ('ผู้ดำเนินการ', {
            'fields': ('created_by',)
        }),
        ('ยอดเงิน', {
            'fields': ('total_amount', 'discount_amount', 'subtotal', 'vat_rate', 'vat_amount', 'grand_total')
        }),
        ('วันที่สร้าง/แก้ไข', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class OrderCounterAdmin(admin.ModelAdmin):
    list_display = ('year', 'counter')
    readonly_fields = ('year', 'counter')

class InvoiceCounterAdmin(admin.ModelAdmin):
    list_display = ('year', 'counter')
    readonly_fields = ('year', 'counter')

admin.site.register(OrderRequest, OrderRequestAdmin)
admin.site.register(PickingOrder, PickingOrderAdmin)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(OrderCounter, OrderCounterAdmin)
admin.site.register(InvoiceCounter, InvoiceCounterAdmin)
admin.site.register(OrderDetail)
admin.site.register(PickingDetail)
