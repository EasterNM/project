from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from .models import Department, Position, CustomUser
from django.contrib.auth.models import Group

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
    list_display = ('username', 'first_name', 'last_name', 'email', 'employee_id', 'position', 'get_department', 'get_groups', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'employee_id')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'position', 'employment_type', 'groups')
    filter_horizontal = ('groups', 'user_permissions')
    
    def get_department(self, obj):
        return obj.department
    get_department.short_description = 'แผนก'
    
    def get_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()]) if obj.groups.exists() else "-"
    get_groups.short_description = 'กลุ่มผู้ใช้'

class CustomGroupAdmin(GroupAdmin):
    list_display = ('name', 'get_users_count', 'get_permissions_count')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    
    def get_users_count(self, obj):
        return obj.user_set.count()
    get_users_count.short_description = 'จำนวนผู้ใช้'
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()
    get_permissions_count.short_description = 'จำนวนสิทธิ์'

class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)

class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('department', 'created_at')

# Unregister the original Group admin
admin.site.unregister(Group)

# Register our CustomUser and other models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Position, PositionAdmin)
admin.site.register(Group, CustomGroupAdmin)
