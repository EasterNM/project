from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Department, Position, CustomUser

class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('ข้อมูลส่วนตัว', {'fields': ('first_name', 'last_name', 'email', 'employee_id', 
                                  'date_of_birth', 'gender', 'nationality', 'phone_number', 
                                  'address', 'emergency_contact', 'profile_image')}),
        ('ข้อมูลการจ้างงาน', {'fields': ('position', 'date_of_joining', 'employment_type', 'manager')}),
        ('สิทธิ์การใช้งาน', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('วันที่สำคัญ', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('username', 'first_name', 'last_name', 'email', 'employee_id', 'position', 'get_department', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'employee_id')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'position', 'employment_type')
    
    def get_department(self, obj):
        return obj.department
    get_department.short_description = 'แผนก'

class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)

class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('department', 'created_at')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Position, PositionAdmin)
