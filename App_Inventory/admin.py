from django.contrib import admin
from .models import (
    Location, InventoryItem, LocationHistory, StockCount, 
    StockCountItem, DamagedItem, SerialCounter
)

class LocationAdmin(admin.ModelAdmin):
    list_display = ('location_name', 'location_code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('location_name', 'location_code')
    readonly_fields = ('created_at', 'updated_at')

class LocationHistoryInline(admin.TabularInline):
    model = LocationHistory
    extra = 0
    readonly_fields = ('move_date', 'from_location', 'to_location', 'moved_by')
    can_delete = False

class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'product', 'status', 'location', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('serial_number', 'product__name')
    readonly_fields = ('serial_number', 'created_at', 'updated_at')
    
    fieldsets = (
        ('ข้อมูลสินค้า', {
            'fields': ('serial_number', 'product', 'status')
        }),
        ('ตำแหน่งและการติดตาม', {
            'fields': ('location', 'lot_number', 'expiry_date')
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [LocationHistoryInline]

class StockCountItemInline(admin.TabularInline):
    model = StockCountItem
    extra = 0
    fields = ('inventory_item', 'product', 'status', 'note')

class StockCountAdmin(admin.ModelAdmin):
    list_display = ('id', 'location', 'status', 'count_date', 'counted_by', 'created_at')
    list_filter = ('status', 'count_date', 'created_at')
    search_fields = ('location__location_name', 'note')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('ข้อมูลการตรวจนับ', {
            'fields': ('location', 'status', 'count_date', 'counted_by')
        }),
        ('ข้อมูลเพิ่มเติม', {
            'fields': ('note',)
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [StockCountItemInline]

class DamagedItemAdmin(admin.ModelAdmin):
    list_display = ('inventory_item', 'status', 'damage_date', 'created_at')
    list_filter = ('status', 'damage_date', 'created_at')
    search_fields = ('inventory_item__serial_number', 'damage_description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('ข้อมูลความเสียหาย', {
            'fields': ('inventory_item', 'status', 'damage_date', 'damage_description')
        }),
        ('การดำเนินการ', {
            'fields': ('repair_cost', 'action_date', 'action_note')
        }),
        ('วันที่', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class SerialCounterAdmin(admin.ModelAdmin):
    list_display = ('id', 'counter')
    readonly_fields = ('counter',)

admin.site.register(Location, LocationAdmin)
admin.site.register(InventoryItem, InventoryItemAdmin)
admin.site.register(StockCount, StockCountAdmin)
admin.site.register(DamagedItem, DamagedItemAdmin)
admin.site.register(SerialCounter, SerialCounterAdmin)
admin.site.register(StockCountItem)
admin.site.register(LocationHistory)
