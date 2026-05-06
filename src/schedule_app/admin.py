from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PVZ, Schedule, GeneratedOrder, LoginAudit, Feedback, EmployeeRating, Notification, OrderStat, OrderDetail, TemporaryOrderData, Task
from .forms import FeedbackAdminForm

@admin.register(TemporaryOrderData)
class TemporaryOrderDataAdmin(admin.ModelAdmin):
    list_display = ['pvz', 'date_range_start', 'date_range_end', 'status', 'created_by', 'created_at', 'imported_at']
    list_filter = ['status', 'pvz', 'created_at']
    search_fields = ['pvz__pvz_name', 'created_by__username']
    readonly_fields = ['generated_data', 'preview_data', 'file_path', 'created_at', 'imported_at', 'created_by']
    
    def has_add_permission(self, request):
        return False  # Запретить добавление через админку
    
    def has_change_permission(self, request, obj=None):
        return False  # Запретить изменение через админку

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'display_pvz', 'is_blocked', 'is_staff')
    list_filter = ('role', 'is_staff', 'pvz', 'is_blocked')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone', 'pvz', 'worked_hours', 'late_count', 'overtime_count', 'is_blocked')}),
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

@admin.register(OrderStat)
class OrderStatAdmin(admin.ModelAdmin):
    list_display = ['pvz', 'order_date', 'total_orders', 'created_at']
    list_filter = ['pvz', 'order_date']
    readonly_fields = ['created_at', 'total_orders']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('pvz', 'order_date')
        }),
        ('Заказы по часам', {
            'fields': (
                'hour_9', 'hour_10', 'hour_11', 'hour_12',
                'hour_13', 'hour_14', 'hour_15', 'hour_16',
                'hour_17', 'hour_18', 'hour_19', 'hour_20'
            )
        }),
        ('Дополнительно', {
            'fields': ('created_at', 'total_orders')
        }),
    )

@admin.register(OrderDetail)
class OrderDetailAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'pvz', 'order_date', 'order_time', 'client_id']
    list_filter = ['pvz', 'order_date']
    search_fields = ['order_number', 'client_id']
    readonly_fields = ['created_at']

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

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    form = FeedbackAdminForm
    list_display = ['client_id', 'pvz', 'overall_rating_pvz', 'created_at']
    list_filter = ['pvz', 'created_at']
    search_fields = ['client_id', 'feedback_text']
    readonly_fields = ['overall_rating_pvz', 'created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('pvz', 'client_id', 'feedback_text')
        }),
        ('Оценки для сотрудников', {
            'fields': ('service_speed', 'employee_politeness', 'employee_competence')
        }),
        ('Оценки для ПВЗ', {
            'fields': ('cleanliness', 'convenient_location')
        }),
        ('Дополнительно', {
            'fields': ('manager_comment', 'created_at', 'overall_rating_pvz')
        }),
    )

@admin.register(EmployeeRating)
class EmployeeRatingAdmin(admin.ModelAdmin):
    list_display = ['employee', 'cleanliness', 'service_speed', 'politeness', 'competence', 'overall_rating', 'created_at']
    list_filter = ['created_at']
    search_fields = ['employee__username', 'employee__first_name', 'employee__last_name']
    readonly_fields = ['overall_rating', 'created_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'pvz', 'assigned_to', 'status', 'priority', 'deadline', 'is_overdue', 'created_at']
    list_filter = ['status', 'priority', 'pvz', 'is_global', 'created_at', 'deadline']
    search_fields = ['title', 'description', 'assigned_to__username', 'assigned_to__first_name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'created_by']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'pvz', 'is_global')
        }),
        ('Назначение', {
            'fields': ('assigned_to', 'created_by')
        }),
        ('Статус и приоритет', {
            'fields': ('status', 'priority', 'deadline')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # При создании
            obj.created_by = request.user
        super().save_model(request, obj, form, change)