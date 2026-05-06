from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PVZ, Schedule, Order, LoginAudit

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'display_pvz', 'is_staff')
    list_filter = ('role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone', 'pvz')}),
    )
    filter_horizontal = ('pvz',)
    
    def display_pvz(self, obj):
        return ", ".join([pvz.pvz_name for pvz in obj.pvz.all()])
    display_pvz.short_description = 'ПВЗ'

@admin.register(PVZ)
class PVZAdmin(admin.ModelAdmin):
    list_display = ['pvz_name', 'pvz_work_schedule']

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['user', 'pvz', 'work_date', 'shift_type', 'shift_start', 'shift_end']
    list_filter = ['pvz', 'work_date', 'shift_type']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'tracking_number', 'created_at', 'status']
    list_filter = ['status', 'created_at']

@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_time', 'ip_address', 'success']
    list_filter = ['success', 'login_time']
    search_fields = ['user__username', 'ip_address']
    readonly_fields = ['user', 'login_time', 'ip_address', 'user_agent', 'success']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False