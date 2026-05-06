from django.urls import path
from . import views

urlpatterns = [
    # Общие страницы
    path('', views.index, name='index'),
    path('profile/', views.profile, name='profile'),
    
    # Страницы администратора
    path('users/', views.users, name='users'),
    path('settings/', views.settings, name='settings'),
    
    # API для управления пользователями админом
    path('api/user/add/', views.api_add_user, name='api_add_user'),
    path('api/user/<int:user_id>/', views.api_get_user, name='api_get_user'),
    path('api/user/<int:user_id>/update/', views.api_update_user, name='api_update_user'),
    path('api/user/<int:user_id>/change-password/', views.api_change_password, name='api_change_password'),
    path('api/user/<int:user_id>/toggle-block/', views.api_toggle_block_user, name='api_toggle_block_user'),
    path('api/user/<int:user_id>/change-role/', views.api_change_role, name='api_change_role'),
    path('api/user/<int:user_id>/delete/', views.api_delete_user, name='api_delete_user'),
    
    # API для управления пользователями менеджером
    path('api/manager/user/add/', views.api_manager_add_user, name='api_manager_add_user'),
    path('api/manager/user/<int:user_id>/', views.api_manager_get_user, name='api_manager_get_user'),
    path('api/manager/user/<int:user_id>/update/', views.api_manager_update_user, name='api_manager_update_user'),
    
    # Страницы менеджера
    path('manager/', views.index_manager, name='index_manager'),
    path('statistics/', views.statistics, name='statistics'),
    path('manager-users/', views.manager_users, name='manager_users'),
    path('notifications/', views.notifications, name='notifications'),
    path('feedbacks/', views.feedbacks, name='feedbacks'),
    path('manager/tasks/', views.manager_tasks, name='manager_tasks'),
   
    # AJAX endpoints для менеджера
    path('add-employee-to-schedule/', views.add_employee_to_schedule, name='add_employee_to_schedule'),
    path('remove-employee-from-schedule/', views.remove_employee_from_schedule, name='remove_employee_from_schedule'),
    path('save-schedule/', views.save_schedule, name='save_schedule'),
    path('get-saved-shifts/', views.get_saved_shifts, name='get_saved_shifts'),
    path('get-available-employees/<int:pvz_id>/', views.get_available_employees, name='get_available_employees'),
    
    # Страницы сотрудника
    path('actual-schedule/', views.actual_schedule, name='actual_schedule'),
    path('schedule-archive/', views.schedule_archive, name='schedule_archive'),
    path('schedule-change-request/', views.schedule_change_request, name='schedule_change_request'),
    path('employee/tasks/', views.employee_tasks, name='employee_tasks'),
    
    # Уведомления
    path('get-notifications/', views.get_notifications, name='get_notifications'),
    path('mark-notification-read/', views.mark_notification_read, name='mark_notification_read'),

    # Генерация заказов
    path('generate-orders/', views.generate_orders, name='generate_orders'),
    path('preview-orders/<int:temp_id>/', views.preview_orders, name='preview_orders'),
    path('download-temp-file/<int:temp_id>/', views.download_temp_file, name='download_temp_file'),
    path('clear-orders/', views.clear_orders, name='clear_orders'),
    
    # API для задач
    path('api/tasks/', views.api_get_tasks, name='api_get_tasks'),
    path('api/tasks/create/', views.api_create_task, name='api_create_task'),
    path('api/tasks/<int:task_id>/update/', views.api_update_task, name='api_update_task'),
    path('api/tasks/<int:task_id>/delete/', views.api_delete_task, name='api_delete_task'),
    path('api/tasks/<int:task_id>/complete/', views.api_complete_task, name='api_complete_task'),
    path('api/tasks/<int:task_id>/status/', views.api_change_task_status, name='api_change_task_status'),
]