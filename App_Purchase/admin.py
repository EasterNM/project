from django.contrib import admin
from .models import (
    PurchaseRequisition, PurchaseRequisitionDetail,
    PurchaseOrder, PurchaseOrderDetail,
    GoodsReceipt, GoodsReceiptDetail,
    POCounter, PRCounter
)

class PurchaseRequisitionDetailInline(admin.TabularInline):
    model = PurchaseRequisitionDetail
    extra = 0
    fields = ('product', 'quantity', 'description')

class PurchaseRequisitionAdmin(admin.ModelAdmin):
    list_display = ('pr_number', 'requested_by', 'status', 'request_date', 'created_at')
    list_filter = ('status', 'request_date', 'created_at')
    search_fields = ('pr_number', 'remarks')
    readonly_fields = ('pr_number', 'created_at', 'updated_at')
    
    fieldsets = (
        ('ข้อมูลคำขอสั่งซื้อ', {
            'fields': ('pr_number', 'requested_by', 'department', 'status', 'request_date', 'required_date')
        }),
        ('ข้อมูลเพิ่มเติม', {
            'fields': ('remarks',)
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PurchaseRequisitionDetailInline]

class PurchaseOrderDetailInline(admin.TabularInline):
    model = PurchaseOrderDetail
    extra = 0
    fields = ('product', 'quantity', 'unit_price', 'subtotal')
    readonly_fields = ('subtotal',)

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'status', 'order_date', 'created_at')
    list_filter = ('status', 'order_date', 'created_at')
    search_fields = ('po_number', 'supplier__company_name')
    readonly_fields = ('po_number', 'created_at', 'updated_at', 'total_amount')
    
    fieldsets = (
        ('ข้อมูลคำสั่งซื้อ', {
            'fields': ('po_number', 'supplier', 'status', 'purchase_requisition', 'created_by')
        }),
        ('วันที่', {
            'fields': ('order_date', 'expected_delivery_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PurchaseOrderDetailInline]

class GoodsReceiptDetailInline(admin.TabularInline):
    model = GoodsReceiptDetail
    extra = 0
    fields = ('purchase_order_detail', 'quantity_received', 'condition', 'notes')

class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_order', 'receipt_date', 'received_by', 'created_at')
    list_filter = ('receipt_date', 'created_at')
    search_fields = ('purchase_order__po_number', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('ข้อมูลการรับสินค้า', {
            'fields': ('purchase_order', 'receipt_date', 'received_by')
        }),
        ('ข้อมูลเพิ่มเติม', {
            'fields': ('notes',)
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [GoodsReceiptDetailInline]

class POCounterAdmin(admin.ModelAdmin):
    list_display = ('id', 'counter')
    readonly_fields = ('counter',)

class PRCounterAdmin(admin.ModelAdmin):
    list_display = ('id', 'counter')
    readonly_fields = ('counter',)

admin.site.register(PurchaseRequisition, PurchaseRequisitionAdmin)
admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
admin.site.register(GoodsReceipt, GoodsReceiptAdmin)
admin.site.register(POCounter, POCounterAdmin)
admin.site.register(PRCounter, PRCounterAdmin)
admin.site.register(PurchaseRequisitionDetail)
admin.site.register(PurchaseOrderDetail)
admin.site.register(GoodsReceiptDetail)
