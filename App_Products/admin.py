from django.contrib import admin
from .models import Category, Brand, Product, Pricing, ProductSupplier, SKUCounter

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_code', 'description')
    search_fields = ('name', 'category_code', 'description')
    list_filter = ('name',)
    ordering = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'category_code', 'description')
        }),
    )

class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand_code', 'description')
    search_fields = ('name', 'brand_code', 'description')
    list_filter = ('name',)
    ordering = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'brand_code', 'description')
        }),
    )

class PricingInline(admin.TabularInline):
    model = Pricing
    extra = 0
    fields = ('price_a', 'price_aa', 'price_aaa', 'effective_date', 'end_date')
    min_num = 0
    max_num = 10
    verbose_name = 'ราคาพิเศษ'
    verbose_name_plural = 'ราคาพิเศษ'

class ProductSupplierInline(admin.TabularInline):
    model = ProductSupplier
    extra = 0
    fields = ('supplier', 'unit_price', 'minimum_order_quantity', 'is_primary_supplier')
    min_num = 0
    max_num = 10
    verbose_name = 'ซัพพลายเออร์'
    verbose_name_plural = 'ซัพพลายเออร์'

class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'brand', 'cost_price', 'price_a', 'price_aa', 'price_aaa', 'reorder_point', 'created_at')
    search_fields = ('sku', 'name', 'description')
    list_filter = ('category', 'brand', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'profit_margin_a')
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('ข้อมูลพื้นฐาน', {
            'fields': ('sku', 'name', 'description', 'category', 'brand', 'unit'),
            'description': 'หากไม่ระบุค่า SKU ระบบจะสร้าง SKU ให้อัตโนมัติในรูปแบบ "รหัสหมวดหมู่-รหัสแบรนด์-ปี-เลขที่"'
        }),
        ('ข้อมูลราคา', {
            'fields': ('cost_price', 'price_a', 'price_aa', 'price_aaa', 'profit_margin_a')
        }),
        ('ข้อมูลคลัง', {
            'fields': ('reorder_point', 'reorder_quantity')
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PricingInline, ProductSupplierInline]
    
    def get_readonly_fields(self, request, obj=None):
        """ทำให้ฟิลด์ SKU เป็น readonly หลังจากสร้างผลิตภัณฑ์แล้ว"""
        if obj: # ถ้าเป็นการแก้ไขออบเจ็กต์ที่มีอยู่แล้ว
            return self.readonly_fields + ('sku',)
        return self.readonly_fields
    
    def profit_margin_a(self, obj):
        return f"{obj.profit_margin_a:.2f}%"
    profit_margin_a.short_description = 'กำไรขั้นต้น (ราคา A)'

class PricingAdmin(admin.ModelAdmin):
    list_display = ('product', 'price_a', 'price_aa', 'price_aaa', 'effective_date', 'end_date')
    search_fields = ('product__name', 'product__sku')
    list_filter = ('effective_date', 'end_date')
    date_hierarchy = 'effective_date'
    
    fieldsets = (
        (None, {
            'fields': ('product', 'price_a', 'price_aa', 'price_aaa', 'effective_date', 'end_date')
        }),
    )
    
    raw_id_fields = ('product',)
    autocomplete_fields = ['product']

class ProductSupplierAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'unit_price', 'minimum_order_quantity', 'is_primary_supplier')
    search_fields = ('product__name', 'product__sku', 'supplier__company_name')
    list_filter = ('is_primary_supplier',)
    list_editable = ('is_primary_supplier',)
    
    fieldsets = (
        (None, {
            'fields': ('product', 'supplier', 'unit_price', 'minimum_order_quantity', 'is_primary_supplier')
        }),
    )
    
    raw_id_fields = ('product', 'supplier')

class SKUCounterAdmin(admin.ModelAdmin):
    list_display = ('year', 'counter')
    readonly_fields = ('year', 'counter')
    search_fields = ('year',)
    ordering = ('-year',)
    list_per_page = 10
    
    def has_add_permission(self, request):
        """SKUCounter ควรถูกสร้างอัตโนมัติเท่านั้น ไม่ควรเพิ่มด้วยตนเอง"""
        return False

# Register models
admin.site.register(Category, CategoryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Pricing, PricingAdmin)
admin.site.register(ProductSupplier, ProductSupplierAdmin)
admin.site.register(SKUCounter, SKUCounterAdmin)
