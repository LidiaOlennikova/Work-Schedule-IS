from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta
from django.shortcuts import render
from .models import Feedback, PVZ, User, EmployeeRating, TemporaryOrderData
from django.db.models import Avg
from .models import Schedule, GeneratedOrder, Notification
import random
from django.db import transaction
from django.contrib import messages
from django.db.models import Sum
from .models import OrderStat, OrderDetail, Task
from .forms import OrderGenerationForm
from django.db import models as django_models 
import pandas as pd
import os
import json
from django.db.models import Q
from django.views.decorators.http import require_http_methods


# ===== ДЕКОРАТОРЫ ДЛЯ ПРОВЕРКИ ПРАВ =====
def admin_required(user):
    """Только для администраторов"""
    return user.is_authenticated and user.role == 'admin'

def manager_required(user):
    """Для менеджеров и администраторов"""
    return user.is_authenticated and user.role in ['manager', 'admin']

def employee_required(user):
    """Для всех авторизованных пользователей"""
    return user.is_authenticated

# ===== ОБЩИЕ СТРАНИЦЫ =====
def index(request):
    """Общая главная страница"""
    return render(request, 'index.html')

@login_required
def profile(request):
    """Страница профиля пользователя"""
    if request.method == 'POST':
        user = request.user
        if 'password_change' in request.POST:
            # Смена пароля
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            if user.check_password(old_password):
                if new_password1 == new_password2 and len(new_password1) >= 8:
                    user.set_password(new_password1)
                    user.save()
                    # Редирект на страницу входа после смены пароля
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, user)
                    return redirect('profile')
        else:
            # Обновление данных профиля
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.phone = request.POST.get('phone', '')
            user.save()
            return redirect('profile')
    
    return render(request, 'profile.html')

# ===== СТРАНИЦЫ АДМИНИСТРАТОРА =====
@login_required
@user_passes_test(admin_required)
def users(request):
    """Страница управления пользователями для админа"""
    users_list = User.objects.all().order_by('-date_joined')
    pvz_list = PVZ.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                
                if action == 'toggle_block':
                    # Блокировка/разблокировка
                    if user != request.user:  # Нельзя блокировать самого себя
                        user.is_blocked = not user.is_blocked
                        user.is_active = not user.is_blocked
                        user.save()
                
                elif action == 'change_role':
                    # Изменение роли
                    new_role = request.POST.get('new_role')
                    if new_role in ['admin', 'manager', 'employee']:
                        if not (user == request.user and new_role != 'admin'):
                            user.role = new_role
                            user.is_staff = new_role == 'admin'
                            user.is_superuser = new_role == 'admin'
                            user.save()
                
                elif action == 'delete_user':
                    # Удаление пользователя
                    if user != request.user:  # Нельзя удалить самого себя
                        user.delete()
                
                elif action == 'add_user':
                    # Добавление нового пользователя
                    username = request.POST.get('username')
                    email = request.POST.get('email')
                    first_name = request.POST.get('first_name')
                    last_name = request.POST.get('last_name')
                    role = request.POST.get('role', 'employee')
                    phone = request.POST.get('phone', '')
                    password = request.POST.get('password')
                    
                    if username and email and password:
                        # Проверяем, что пользователь не существует
                        if not User.objects.filter(username=username).exists():
                            user = User.objects.create(
                                username=username,
                                email=email,
                                first_name=first_name,
                                last_name=last_name,
                                role=role,
                                phone=phone,
                                is_staff=role == 'admin',
                                is_superuser=role == 'admin'
                            )
                            user.set_password(password)
                            user.save()
                            
                            # Добавляем ПВЗ
                            pvz_ids = request.POST.getlist('pvz')
                            for pvz_id in pvz_ids:
                                try:
                                    pvz = PVZ.objects.get(id=pvz_id)
                                    user.pvz.add(pvz)
                                except PVZ.DoesNotExist:
                                    pass
            
            except User.DoesNotExist:
                pass
        
        return redirect('users')
    
    context = {
        'users': users_list,
        'pvz_list': pvz_list
    }
    return render(request, 'users.html', context)

@login_required
@user_passes_test(admin_required)
def settings(request):
    """Настройки системы (только для админов)"""
    if request.method == 'POST':
        # Здесь можно добавить логику для обработки сохранения настроек
        pass
    
    context = {
        'system_settings': {
            'company_name': 'WorkSchedule IS',
            'timezone': 'Europe/Moscow',
            'work_week_start': 'monday',
            'shift_duration': 12,
            'crm_sync_enabled': True,
            'sync_interval': 30,
            'auto_backup': True,
        },
        'backup_files': [
            {'name': 'backup_2025_10_22_1430.sql', 'date': '22.10.2025 14:30', 'size': '2.4 MB'},
            {'name': 'backup_2025_10_21_0300.sql', 'date': '21.10.2025 03:00', 'size': '2.3 MB'},
            {'name': 'backup_2025_10_20_0300.sql', 'date': '20.10.2025 03:00', 'size': '2.3 MB'},
        ],
        'system_logs': [
            {'time': '22.10.2025 14:25:03', 'level': 'info', 'user': 'valeria_bolgar', 'action': 'Просмотр графика', 'details': 'Пользователь просмотрел свой график на октябрь'},
            {'time': '22.10.2025 14:20:15', 'level': 'warning', 'user': 'system', 'action': 'Синхронизация с CRM', 'details': 'Пропущено 2 записи при синхронизации'},
            {'time': '22.10.2025 14:15:42', 'level': 'error', 'user': 'test_admin', 'action': 'Изменение графика', 'details': 'Ошибка валидации данных смены'},
        ]
    }
    return render(request, 'settings.html', context)

# ===== API ФУНКЦИИ ДЛЯ AJAX =====
@login_required
@user_passes_test(admin_required)
@csrf_exempt
def api_toggle_block_user(request, user_id):
    """API: Блокировка/разблокировка пользователя"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            
            # Нельзя блокировать самого себя
            if user == request.user:
                return JsonResponse({'success': False, 'error': 'Нельзя блокировать самого себя'})
            
            user.is_blocked = not user.is_blocked
            user.is_active = not user.is_blocked
            user.save()
            
            status = 'заблокирован' if user.is_blocked else 'разблокирован'
            return JsonResponse({
                'success': True,
                'message': f'Пользователь {status}',
                'is_blocked': user.is_blocked
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def api_change_role(request, user_id):
    """API: Изменение роли пользователя"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_role = data.get('role')
            
            if new_role not in ['admin', 'manager', 'employee']:
                return JsonResponse({'success': False, 'error': 'Неверная роль'})
            
            user = User.objects.get(id=user_id)
            
            # Нельзя понизить роль самому себе
            if user == request.user and new_role != 'admin':
                return JsonResponse({'success': False, 'error': 'Нельзя понизить свою роль'})
            
            user.role = new_role
            user.is_staff = new_role == 'admin'
            user.is_superuser = new_role == 'admin'
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Роль изменена на {user.get_role_display()}',
                'role': user.role,
                'role_display': user.get_role_display()
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def api_delete_user(request, user_id):
    """API: Удаление пользователя"""
    if request.method == 'DELETE':
        try:
            user = User.objects.get(id=user_id)
            
            # Нельзя удалить самого себя
            if user == request.user:
                return JsonResponse({'success': False, 'error': 'Нельзя удалить самого себя'})
            
            username = user.username
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Пользователь {username} удален'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def api_add_user(request):
    """API: Добавление нового пользователя"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            role = data.get('role', 'employee')
            phone = data.get('phone', '').strip()
            password = data.get('password', '').strip()
            pvz_ids = data.get('pvz_ids', [])
            
            # Проверка обязательных полей
            if not username or not email or not password:
                return JsonResponse({'success': False, 'error': 'Заполните обязательные поля'})
            
            # Проверка существующего пользователя
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'error': 'Пользователь с таким логином уже существует'})
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'Пользователь с таким email уже существует'})
            
            # Создание пользователя
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                phone=phone,
                is_staff=role == 'admin',
                is_superuser=role == 'admin'
            )
            user.set_password(password)
            user.save()
            
            # Добавление ПВЗ
            for pvz_id in pvz_ids:
                try:
                    pvz = PVZ.objects.get(id=pvz_id)
                    user.pvz.add(pvz)
                except PVZ.DoesNotExist:
                    pass
            
            return JsonResponse({
                'success': True,
                'message': f'Пользователь {username} успешно создан',
                'user_id': user.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@user_passes_test(admin_required)
def api_get_user(request, user_id):
    """API: Получение данных пользователя"""
    try:
        user = User.objects.get(id=user_id)
        pvz_ids = list(user.pvz.values_list('id', flat=True))
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'role': user.role,
                'role_display': user.get_role_display(),
                'phone': user.phone,
                'is_blocked': user.is_blocked,
                'is_active': user.is_active,
                'date_joined': user.date_joined.strftime('%d.%m.%Y %H:%M'),
                'last_login': user.last_login.strftime('%d.%m.%Y %H:%M') if user.last_login else None,
                'pvz_ids': pvz_ids
            }
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пользователь не найден'})

# ===== СТРАНИЦЫ МЕНЕДЖЕРА =====
@login_required
@user_passes_test(manager_required)
def index_manager(request):
    """Главная страница менеджера (для менеджеров и админов)"""
    # Получаем текущий месяц
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    
    # Получаем список ПВЗ, доступных текущему пользователю
    if request.user.role == 'admin':
        pvz_list = PVZ.objects.all()
    else:
        pvz_list = request.user.pvz.all()
    
    # Получаем выбранный ПВЗ
    selected_pvz_id = request.GET.get('pvz_id')
    if selected_pvz_id and pvz_list.filter(id=selected_pvz_id).exists():
        current_pvz = PVZ.objects.get(id=selected_pvz_id)
        employees = User.objects.filter(role='employee', pvz=current_pvz)
    else:
        current_pvz = pvz_list.first() if pvz_list.exists() else None
        employees = User.objects.filter(role='employee', pvz=current_pvz) if current_pvz else User.objects.none()
    
    # Получаем доступных сотрудников для добавления (только из доступных ПВЗ)
    available_employees = User.objects.filter(role='employee').exclude(id__in=employees.values('id'))
    
    # Генерируем данные для двух месяцев (текущий и следующий)
    months_data = []
    
    for month_offset in [0, 1]:  # Текущий и следующий месяц
        year = current_year
        month = current_month + month_offset
        
        # Корректируем год и месяц если вышли за пределы
        if month > 12:
            month -= 12
            year += 1
        
        # Генерируем дни месяца
        import calendar
        cal = calendar.Calendar(firstweekday=0)
        
        month_days = []
        for day in cal.itermonthdays(year, month):
            if day != 0:
                date_obj = datetime(year, month, day).date()
                month_days.append({
                    'day_number': day,
                    'date': date_obj,
                    'weekday_short': ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][date_obj.weekday()]
                })
        
        # Разделяем на две половины
        total_days = len(month_days)
        split_index = (total_days + 1) // 2
        
        first_half_days = month_days[:split_index]
        second_half_days = month_days[split_index:]
        
        # Подготавливаем данные сотрудников с реальными сменами
        employees_data = []
        for employee in employees:
            # Получаем ВСЕ смены сотрудника за месяц для текущего ПВЗ
            schedules = Schedule.objects.filter(
                user=employee, 
                pvz=current_pvz,
                work_date__year=year,
                work_date__month=month
            )
            
            # Создаем словарь смен в формате { '2025-10-01': 'full', ... }
            schedule_dict = {}
            for schedule in schedules:
                schedule_dict[schedule.work_date.isoformat()] = schedule.shift_type
            
            employees_data.append({
                'id': employee.id,
                'name': employee.get_full_name() or employee.username,
                'pvz': current_pvz.pvz_name if current_pvz else '',
                'schedules': schedule_dict,  # Передаем словарь смен
                'first_half_days': first_half_days,
                'second_half_days': second_half_days
            })
        
        months_data.append({
            'year': year,
            'month': month,
            'month_name': ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                          'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'][month - 1],
            'first_half_days': first_half_days,
            'second_half_days': second_half_days,
            'employees': employees_data
        })
    
    context = {
        'months_data': months_data,
        'pvz_list': pvz_list,
        'employees': employees,
        'current_pvz': current_pvz,
        'available_employees': available_employees,
    }
    return render(request, 'index_manager.html', context)


# ===== СТРАНИЦА МЕНЕДЖЕРА ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ=====
def manager_users(request):
    """Страница управления пользователями для менеджера"""
    # Менеджер видит ВСЕХ пользователей своих ПВЗ, включая админов и других менеджеров
    users = User.objects.filter(pvz__in=request.user.pvz.all()).distinct()
    
    context = {
        'users': users
    }
    return render(request, 'users.html', context)

def get_available_employees(request, pvz_id):
    """Получить всех доступных сотрудников для ПВЗ (включая админов и менеджеров)"""
    pvz = PVZ.objects.get(id=pvz_id)
    # Включаем ВСЕХ пользователей привязанных к этому ПВЗ, независимо от роли
    available_users = User.objects.filter(pvz=pvz)
    
    return JsonResponse({
        'users': list(available_users.values('id', 'first_name', 'last_name', 'role'))
    })

@login_required
@user_passes_test(manager_required)
def get_saved_shifts(request):
    """AJAX: Получение сохраненных смен"""
    pvz_id = request.GET.get('pvz_id')
    if not pvz_id:
        return JsonResponse({'success': False, 'error': 'No PVZ selected'})
    
    try:
        # Получаем смены для выбранного ПВЗ
        schedules = Schedule.objects.filter(pvz_id=pvz_id)
        
        shifts_data = []
        for schedule in schedules:
            shifts_data.append({
                'employee_id': schedule.user_id,
                'date': schedule.work_date.isoformat(),
                'shift_type': schedule.shift_type
            })
        
        return JsonResponse({'success': True, 'shifts': shifts_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(manager_required)
@csrf_exempt
def add_employee_to_schedule(request):
    """AJAX: Добавление сотрудника к графику"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            employee_id = data.get('employee_id')
            pvz_id = data.get('pvz_id')
            
            employee = User.objects.get(id=employee_id)
            pvz = PVZ.objects.get(id=pvz_id)
            
            # Добавляем сотрудника к ПВЗ
            employee.pvz.add(pvz)
            
            return JsonResponse({'success': True, 'message': 'Сотрудник добавлен к графику'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(manager_required)
@csrf_exempt
def remove_employee_from_schedule(request):
    """AJAX: Удаление сотрудника из графика"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            employee_id = data.get('employee_id')
            pvz_id = data.get('pvz_id')
            
            employee = User.objects.get(id=employee_id)
            pvz = PVZ.objects.get(id=pvz_id)
            
            # Удаляем сотрудника из ПВЗ
            employee.pvz.remove(pvz)
            
            return JsonResponse({'success': True, 'message': 'Сотрудник удален из графика'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(manager_required)
@csrf_exempt
def save_schedule(request):
    """AJAX: Сохранение графика"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            changes = data.get('changes', [])
            notify_employees = data.get('notify_employees', False)
            pvz_id = data.get('pvz_id')
            
            pvz = PVZ.objects.get(id=pvz_id)
            affected_employees = set()
            
            # Сохраняем изменения в базу
            for change in changes:
                employee_id = change['employee_id']
                date = change['date']
                shift_type = change['shift_type']
                
                # Сначала удаляем ВСЕ существующие записи для этой даты и сотрудника
                Schedule.objects.filter(
                    user_id=employee_id,
                    pvz_id=pvz_id,
                    work_date=date
                ).delete()
                
                # Создаем новую запись только если выбран тип смены
                if shift_type:  # Только если не пустое значение
                    Schedule.objects.create(
                        user_id=employee_id,
                        pvz_id=pvz_id,
                        work_date=date,
                        shift_type=shift_type,
                        shift_start='09:00',
                        shift_end='21:00',
                    )
                    affected_employees.add(employee_id)
            
            # Если нужно уведомить сотрудников
            if notify_employees and affected_employees:
                # Получаем сотрудников для уведомления
                employees_to_notify = User.objects.filter(id__in=affected_employees)
                
                for employee in employees_to_notify:
                    # Создаем уведомление в базе
                    Notification.objects.create(
                        user=employee,
                        notification_type='schedule_change',
                        title=f'Изменения в графике - {pvz.pvz_name}',
                        message=f'В вашем рабочем графике в пункте "{pvz.pvz_name}" произошли изменения. Пожалуйста, проверьте актуальный график в системе.',
                        related_pvz=pvz
                    )
                
            return JsonResponse({'success': True, 'message': 'График сохранен', 'notified': notify_employees})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})



# ===== СТРАНИЦЫ ЗАДАЧ =====

@login_required
def api_get_tasks(request):
    """API: Получение списка задач"""
    try:
        user = request.user
        
        if user.role in ['manager', 'admin']:
            # Менеджеры и админы видят задачи по своим ПВЗ
            if user.role == 'admin':
                tasks = Task.objects.all()
            else:
                manager_pvz = user.pvz.all()
                tasks = Task.objects.filter(pvz__in=manager_pvz)
        else:
            # Сотрудники видят свои задачи и общие задачи своего ПВЗ
            employee_pvz = user.pvz.all()
            tasks = Task.objects.filter(
                Q(assigned_to=user) | 
                Q(pvz__in=employee_pvz, is_global=True)
            ).distinct()
        
        # Фильтрация по параметрам
        status = request.GET.get('status')
        if status:
            tasks = tasks.filter(status=status)
        
        pvz_id = request.GET.get('pvz_id')
        if pvz_id:
            tasks = tasks.filter(pvz_id=pvz_id)
        
        assigned_to = request.GET.get('assigned_to')
        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)
        
        # Сортировка
        tasks = tasks.order_by('-created_at')
        
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'pvz_id': task.pvz_id,
                'pvz_name': task.pvz.pvz_name if task.pvz else '',
                'assigned_to_id': task.assigned_to_id,
                'assigned_to_name': task.assigned_to.get_full_name() if task.assigned_to else 'Все сотрудники',
                'status': task.status,
                'status_display': task.get_status_display(),
                'priority': task.priority,
                'priority_display': task.get_priority_display(),
                'deadline': task.deadline.isoformat() if task.deadline else None,
                'is_global': task.is_global,
                'is_overdue': task.is_overdue,
                'created_at': task.created_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'created_by_name': task.created_by.get_full_name() if task.created_by else None,
            })
        
        return JsonResponse({
            'success': True,
            'tasks': tasks_data,
            'total': len(tasks_data)
        })
        
    except Exception as e:
        import traceback
        print(f"Error in api_get_tasks: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(manager_required)
@csrf_exempt
def api_create_task(request):
    """API: Создание новой задачи"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Проверка прав на ПВЗ
            pvz = PVZ.objects.get(id=data['pvz_id'])
            if request.user.role != 'admin' and pvz not in request.user.pvz.all():
                return JsonResponse({'success': False, 'error': 'Нет прав на создание задач для этого ПВЗ'})
            
            task = Task.objects.create(
                title=data['title'],
                description=data.get('description', ''),
                pvz=pvz,
                created_by=request.user,
                priority=data.get('priority', 'medium'),
                is_global=data.get('is_global', False),
            )
            
            # Назначение сотрудника
            if data.get('assigned_to_id'):
                try:
                    assigned_user = User.objects.get(id=data['assigned_to_id'])
                    if assigned_user.role == 'employee':
                        task.assigned_to = assigned_user
                except User.DoesNotExist:
                    pass
            
            # Срок выполнения
            if data.get('deadline'):
                task.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
            
            task.save()
            
            # Создаем уведомления
            if task.assigned_to:
                Notification.objects.create(
                    user=task.assigned_to,
                    notification_type='system',
                    title='Новая задача',
                    message=f'Вам назначена задача "{task.title}" в ПВЗ {task.pvz.pvz_name}',
                    related_pvz=task.pvz
                )
            elif task.is_global:
                # Уведомляем всех сотрудников ПВЗ
                employees = User.objects.filter(role='employee', pvz=task.pvz)
                for employee in employees:
                    Notification.objects.create(
                        user=employee,
                        notification_type='system',
                        title='Новая общая задача',
                        message=f'Новая задача для ПВЗ {task.pvz.pvz_name}: "{task.title}"',
                        related_pvz=task.pvz
                    )
            
            return JsonResponse({
                'success': True,
                'message': 'Задача успешно создана',
                'task_id': task.id
            })
            
        except PVZ.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'ПВЗ не найден'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Неверный формат данных'})
        except Exception as e:
            import traceback
            print(f"Error in api_create_task: {traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


@login_required
@csrf_exempt
def api_complete_task(request, task_id):
    """API: Отметить задачу как выполненную"""
    if request.method == 'POST':
        try:
            task = Task.objects.get(id=task_id)
            
            # Проверка прав
            if request.user.role == 'employee':
                # Сотрудник может выполнять только свои задачи или общие задачи своего ПВЗ
                if not (task.assigned_to == request.user or 
                       (task.is_global and task.pvz in request.user.pvz.all())):
                    return JsonResponse({'success': False, 'error': 'Нет прав на выполнение этой задачи'})
            
            # Проверяем, не выполнена ли уже задача
            if task.status == 'completed':
                return JsonResponse({'success': False, 'error': 'Задача уже выполнена'})
            
            task.complete(request.user)
            
            return JsonResponse({
                'success': True,
                'message': 'Задача отмечена как выполненная',
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            })
            
        except Task.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Задача не найдена'})
        except Exception as e:
            import traceback
            print(f"Error in api_complete_task: {traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


@login_required
@user_passes_test(manager_required)
@csrf_exempt
def api_delete_task(request, task_id):
    """API: Удаление задачи"""
    if request.method == 'DELETE':
        try:
            task = Task.objects.get(id=task_id)
            
            # Проверка прав
            if request.user.role != 'admin' and task.pvz not in request.user.pvz.all():
                return JsonResponse({'success': False, 'error': 'Нет прав на удаление этой задачи'})
            
            task_title = task.title
            task.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Задача "{task_title}" удалена'
            })
            
        except Task.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Задача не найдена'})
        except Exception as e:
            import traceback
            print(f"Error in api_delete_task: {traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


@login_required
@user_passes_test(manager_required)
@csrf_exempt
def api_update_task(request, task_id):
    """API: Обновление задачи"""
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            task = Task.objects.get(id=task_id)
            
            # Проверка прав
            if request.user.role != 'admin' and task.pvz not in request.user.pvz.all():
                return JsonResponse({'success': False, 'error': 'Нет прав на редактирование этой задачи'})
            
            # Обновление полей
            if 'title' in data:
                task.title = data['title']
            if 'description' in data:
                task.description = data['description']
            if 'priority' in data:
                task.priority = data['priority']
            if 'is_global' in data:
                task.is_global = data['is_global']
            if 'deadline' in data and data['deadline']:
                task.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
            if 'assigned_to_id' in data:
                if data['assigned_to_id']:
                    try:
                        task.assigned_to = User.objects.get(id=data['assigned_to_id'])
                    except User.DoesNotExist:
                        pass
                else:
                    task.assigned_to = None
            
            task.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Задача обновлена'
            })
            
        except Task.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Задача не найдена'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Неверный формат данных'})
        except Exception as e:
            import traceback
            print(f"Error in api_update_task: {traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


@login_required
@user_passes_test(manager_required)
@csrf_exempt
def api_change_task_status(request, task_id):
    """API: Изменение статуса задачи"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            
            task = Task.objects.get(id=task_id)
            
            # Проверка прав
            if request.user.role != 'admin' and task.pvz not in request.user.pvz.all():
                return JsonResponse({'success': False, 'error': 'Нет прав на изменение этой задачи'})
            
            valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
            if new_status in valid_statuses:
                old_status = task.status
                task.status = new_status
                
                if new_status == 'completed' and not task.completed_at:
                    task.completed_at = timezone.now()
                elif new_status != 'completed':
                    task.completed_at = None
                
                task.save()
                
                # Уведомление исполнителю
                if task.assigned_to and old_status != new_status:
                    Notification.objects.create(
                        user=task.assigned_to,
                        notification_type='system',
                        title='Изменен статус задачи',
                        message=f'Статус задачи "{task.title}" изменен на "{task.get_status_display()}"',
                        related_pvz=task.pvz
                    )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Статус изменен на {task.get_status_display()}',
                    'status': task.status
                })
            
            return JsonResponse({'success': False, 'error': 'Неверный статус'})
            
        except Task.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Задача не найдена'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Неверный формат данных'})
        except Exception as e:
            import traceback
            print(f"Error in api_change_task_status: {traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


# ===== СТРАНИЦЫ ЗАДАЧ =====

@login_required
@user_passes_test(manager_required)
def manager_tasks(request):
    """Страница управления задачами для менеджера"""
    if request.user.role == 'admin':
        pvz_list = PVZ.objects.all()
        employees = User.objects.filter(role='employee')
    else:
        pvz_list = request.user.pvz.all()
        employees = User.objects.filter(role='employee', pvz__in=pvz_list).distinct()
    
    context = {
        'pvz_list': pvz_list,
        'employees': employees,
    }
    return render(request, 'manager_tasks.html', context)


@login_required
def employee_tasks(request):
    """Страница задач для сотрудника"""
    employee_pvz = request.user.pvz.all()
    
    context = {
        'employee_pvz': employee_pvz,
    }
    return render(request, 'employee_tasks.html', context)


@login_required
@user_passes_test(manager_required)
def notifications(request):
    """Управление уведомлениями (для менеджеров и админов)"""
    return render(request, 'notifications.html')

@login_required
@user_passes_test(manager_required)
def feedbacks(request):
    # Получаем все ПВЗ
    pvz_list = PVZ.objects.all()
    pvz_with_details = []
    
    for pvz in pvz_list:
        # Получаем отзывы для этого ПВЗ
        feedbacks_for_pvz = Feedback.objects.filter(pvz=pvz)
        
        # Подсчет рейтингов по критериям
        criteria_data = {
            'service_speed': {'sum': 0, 'count': 0, 'name': 'Скорость'},
            'employee_politeness': {'sum': 0, 'count': 0, 'name': 'Вежливость'},
            'employee_competence': {'sum': 0, 'count': 0, 'name': 'Компетентность'},
            'cleanliness': {'sum': 0, 'count': 0, 'name': 'Чистота'},
            'convenient_location': {'sum': 0, 'count': 0, 'name': 'Расположение'},
        }
        
        for feedback in feedbacks_for_pvz:
            for field in criteria_data.keys():
                value = getattr(feedback, field)
                if value is not None:
                    criteria_data[field]['sum'] += value
                    criteria_data[field]['count'] += 1
        
        # Подготавливаем данные для шаблона
        rating_details = []
        for key, data in criteria_data.items():
            if data['count'] > 0:
                value = data['sum'] / data['count']
            else:
                value = 0
            
            try:
                # Преобразуем к float
                value_float = float(value)
                
                # Ограничиваем диапазон
                if value_float < 1.0:
                    value_float = 1.0
                elif value_float > 5.0:
                    value_float = 5.0
                
                # Расчет процента: 1→20%, 2→40%, 3→60%, 4→80%, 5→100%
                percentage = ((value_float - 1.0) / 4.0) * 100
                
                # Округляем для отображения и гарантируем целое число
                display_value = round(value_float, 2)
                # Преобразуем к строке с точкой для HTML
                display_percentage = f"{round(percentage, 1)}"
                
            except (ValueError, TypeError):
                display_value = 0
                display_percentage = "20"  # Минимальный процент
                value_float = 1.0
            
            rating_details.append({
                'name': data['name'],
                'value': display_value,
                'percentage': display_percentage,  # Строка с точкой
                'count': data['count'],
                'gradient_color': get_gradient_color(value_float)
            })
        
        # Расчет общего рейтинга ПВЗ
        if feedbacks_for_pvz.exists():
            overall_rating = sum(detail['value'] for detail in rating_details) / len(rating_details)
        else:
            overall_rating = 0
        
        pvz_data = {
            'id': pvz.id,
            'pvz_name': pvz.pvz_name,
            'overall_rating': round(overall_rating, 2),
            'rating_details': rating_details
        }
        
        pvz_with_details.append(pvz_data)
    
    # Получаем сотрудников с детальными рейтингами и связью с ПВЗ
    employees = User.objects.filter(role='employee')
    employees_with_details = []
    
    for employee in employees:
        # Получаем оценки этого сотрудника из модели EmployeeRating
        employee_ratings = EmployeeRating.objects.filter(employee=employee)
        
        # Подсчет рейтингов по критериям
        criteria_data = {
            'cleanliness': {'sum': 0, 'count': 0, 'name': 'Чистота'},
            'service_speed': {'sum': 0, 'count': 0, 'name': 'Скорость'},
            'politeness': {'sum': 0, 'count': 0, 'name': 'Вежливость'},
            'competence': {'sum': 0, 'count': 0, 'name': 'Компетентность'},
        }
        
        for rating in employee_ratings:
            for field in criteria_data.keys():
                value = getattr(rating, field)
                criteria_data[field]['sum'] += value
                criteria_data[field]['count'] += 1
        
        # Подготавливаем данные для шаблона
        rating_details = []
        average_rating = 0
        total_criteria = 0
        
        for key, data in criteria_data.items():
            if data['count'] > 0:
                value = data['sum'] / data['count']
                average_rating += value
                total_criteria += 1
            else:
                value = 0
            
            # РАСЧЕТ ПРОЦЕНТОВ
            # Оценка от 1 до 5, процент от 20% до 100%
            percentage = ((float(value) - 1.0) / 4.0) * 100
            
            rating_details.append({
                'name': data['name'],
                'value': round(value, 2),
                'percentage': percentage,  # Важно: передаем число, не строку!
                'count': data['count'],
                'gradient_color': get_gradient_color(value)
            })
        
        # Расчет общего среднего рейтинга
        if total_criteria > 0:
            average_rating = average_rating / total_criteria
        
        # Получаем ПВЗ, с которыми связан сотрудник через его расписание или оценки
        # 1. ПВЗ из расписания сотрудника
        schedule_pvz_ids = Schedule.objects.filter(user=employee).values_list('pvz_id', flat=True).distinct()
        # 2. ПВЗ, к которым привязан сотрудник через ManyToMany поле
        employee_pvz_ids = list(employee.pvz.values_list('id', flat=True))
        
        # Объединяем все ПВЗ сотрудника
        all_pvz_ids = list(set(list(schedule_pvz_ids) + employee_pvz_ids))
        employee_pvz = PVZ.objects.filter(id__in=all_pvz_ids)
        
        employee_data = {
            'id': employee.id,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'average_rating': round(average_rating, 2),
            'rating_details': rating_details,
            'full_name': f"{employee.first_name} {employee.last_name}",
            'pvz': employee_pvz,  # Все ПВЗ сотрудника
            'pvz_ids': all_pvz_ids  # Список ID ПВЗ для фильтрации
        }
            
        employees_with_details.append(employee_data)
    
    # Получаем последние отзывы
    feedbacks_list = Feedback.objects.all().order_by('-created_at')[:20]
    
    context = {
        'pvz_list': pvz_with_details,
        'employees': employees_with_details,
        'feedbacks': feedbacks_list,
    }
    
    return render(request, 'feedbacks.html', context)

def get_gradient_color(rating):
    """Функция для получения градиентного цвета на основе оценки"""
    # Цвета для разных оценок (от красного к зеленому)
    color_stops = [
        (1.0, '#8B0000'),   # Темно-красный
        (1.5, '#B22222'),   # Огненно-красный
        (2.0, '#FF0000'),   # Красный
        (2.5, '#FF4500'),   # Красно-оранжевый
        (3.0, '#FFA500'),   # Оранжевый
        (3.5, '#FFD700'),   # Золотой
        (4.0, '#9ACD32'),   # Желто-зеленый
        (4.5, '#98FB98'),   # Светло-зеленый
        (5.0, '#7CFC00'),   # Ярко-зеленый
    ]
    
    # Если оценка меньше 1 или больше 5, ограничиваем её
    if rating < 1.0:
        rating = 1.0
    if rating > 5.0:
        rating = 5.0
    
    # Находим два ближайших значения для интерполяции
    lower_stop = color_stops[0]
    upper_stop = color_stops[-1]
    
    for i in range(len(color_stops) - 1):
        if rating >= color_stops[i][0] and rating <= color_stops[i + 1][0]:
            lower_stop = color_stops[i]
            upper_stop = color_stops[i + 1]
            break
    
    # Если оценка точно совпадает с одним из стоп-значений
    if rating == lower_stop[0]:
        return lower_stop[1]
    if rating == upper_stop[0]:
        return upper_stop[1]
    
    # Интерполируем между двумя цветами
    ratio = (rating - lower_stop[0]) / (upper_stop[0] - lower_stop[0])
    
    # Функция для интерполяции цвета
    def interpolate_hex_color(color1, color2, factor):
        r1 = int(color1[1:3], 16)
        g1 = int(color1[3:5], 16)
        b1 = int(color1[5:7], 16)
        
        r2 = int(color2[1:3], 16)
        g2 = int(color2[3:5], 16)
        b2 = int(color2[5:7], 16)
        
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    return interpolate_hex_color(lower_stop[1], upper_stop[1], ratio)

# ===== СТРАНИЦЫ СОТРУДНИКА =====
@login_required
def actual_schedule(request):
    """График сотрудника (для всех авторизованных)"""
    # Получаем доступные ПВЗ для текущего пользователя
    available_pvz = request.user.pvz.all()
    
    # Получаем выбранный ПВЗ
    selected_pvz_id = request.GET.get('pvz')
    if selected_pvz_id and available_pvz.filter(id=selected_pvz_id).exists():
        selected_pvz = PVZ.objects.get(id=selected_pvz_id)
    else:
        selected_pvz = available_pvz.first() if available_pvz.exists() else None
    
    # Генерируем данные для двух месяцев (текущий и следующий)
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    
    months_data = []
    
    for month_offset in [0, 1]:  # Текущий и следующий месяц
        year = current_year
        month = current_month + month_offset
        
        # Корректируем год и месяц если вышли за пределы
        if month > 12:
            month -= 12
            year += 1
        
        # Генерируем дни месяца
        import calendar
        cal = calendar.Calendar(firstweekday=0)
        
        month_days = []
        for day in cal.itermonthdays(year, month):
            if day != 0:
                month_days.append({
                    'day_number': day,
                    'date': datetime(year, month, day).date(),
                    'weekday_short': ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][datetime(year, month, day).weekday()]
                })
        
        # Разделяем на две половины
        total_days = len(month_days)
        split_index = (total_days + 1) // 2
        
        first_half_days = month_days[:split_index]
        second_half_days = month_days[split_index:]
        
        # Подготавливаем данные сотрудников
        employees_data = []
        
        if selected_pvz:
            # ПОКАЗЫВАЕМ ТОЛЬКО СОТРУДНИКОВ (employee), а не менеджеров и админов
            employees = User.objects.filter(role='employee', pvz=selected_pvz)
            
            for employee in employees:
                # Получаем реальные смены из базы
                schedules = Schedule.objects.filter(
                    user=employee, 
                    pvz=selected_pvz,
                    work_date__year=year,
                    work_date__month=month
                ).order_by('work_date')
                
                # Создаем словарь смен для быстрого доступа по дате
                schedule_dict = {}
                for schedule in schedules:
                    schedule_dict[schedule.work_date.day] = schedule.get_shift_type_display()
                
                # Заполняем смены для первой половины
                schedule_first_half = []
                for day in first_half_days:
                    shift = schedule_dict.get(day['day_number'])
                    schedule_first_half.append(shift)
                
                # Заполняем смены для второй половины
                schedule_second_half = []
                for day in second_half_days:
                    shift = schedule_dict.get(day['day_number'])
                    schedule_second_half.append(shift)
                
                employees_data.append({
                    'id': employee.id,
                    'name': employee.get_full_name() or employee.username,
                    'pvz': selected_pvz.pvz_name,
                    'is_current_user': employee.id == request.user.id,
                    'schedule_first_half': schedule_first_half,
                    'schedule_second_half': schedule_second_half
                })
        
        months_data.append({
            'year': year,
            'month': month,
            'month_name': ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                          'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'][month - 1],
            'first_half_days': first_half_days,
            'second_half_days': second_half_days,
            'employees': employees_data
        })
    
    context = {
        'months_data': months_data,
        'available_pvz': available_pvz,
        'selected_pvz': selected_pvz,
    }
    return render(request, 'actual_schedule.html', context)

@login_required
def schedule_archive(request):
    """Страница архива графиков с реальными данными из базы"""
    # Получаем текущего пользователя
    current_user = request.user
    
    # Определяем, какие данные показывать в зависимости от роли
    if current_user.role in ['manager', 'admin']:
        # Для менеджеров и админов показываем данные всех сотрудников их ПВЗ
        if current_user.role == 'admin':
            employees = User.objects.filter(role='employee')
        else:
            # Получаем ПВЗ менеджера и сотрудников этих ПВЗ
            manager_pvz = current_user.pvz.all()
            employees = User.objects.filter(role='employee', pvz__in=manager_pvz)
    else:
        # Для сотрудников показываем только их данные
        employees = User.objects.filter(id=current_user.id)
    
    # Создаем архивные данные
    archive_data = []
    
    # Месяцы для отображения (с июня по текущий месяц)
    current_year = datetime.now().year
    months = [
        (6, 'Июнь', 2025),
        (7, 'Июль', 2025), 
        (8, 'Август', 2025),
        (9, 'Сентябрь', 2025),
        (10, 'Октябрь', 2025),
    ]
    
    # Продолжительность смены в часах
    SHIFT_DURATION_HOURS = 12
    
    for month_num, month_name, year in months:
        # Для каждого месяца собираем статистику
        month_schedules = Schedule.objects.filter(
            user__in=employees,
            work_date__year=year,
            work_date__month=month_num
        )
        
        # Подсчет статистики
        total_shifts = month_schedules.count()
        
        # Считаем опоздания и переработки
        late_count = month_schedules.filter(shift_type='late').count()
        overtime_count = month_schedules.filter(shift_type='overtime').count()
        
        # Загруженность (процент от 15 смен - 100%)
        workload_percentage = min(100, int((total_shifts / 15) * 100)) if total_shifts > 0 else 0
        
        # Общее время (12 часов за смену)
        total_hours = total_shifts * SHIFT_DURATION_HOURS
        
        archive_data.append({
            'month_num': month_num,
            'month_name': month_name,
            'year': year,
            'total_shifts': total_shifts,
            'total_hours': total_hours,
            'late_count': late_count,
            'overtime_count': overtime_count,
            'workload_percentage': workload_percentage,
            'schedules_count': month_schedules.count()
        })
    
    context = {
        'archive_data': archive_data,
    }
    return render(request, 'schedule_archive.html', context)

@login_required
def schedule_change_request(request):
    """Обработка запроса на изменение графика от сотрудника (смена или выходной)"""
    if request.method == 'POST':
        try:
            # Получаем данные из формы запроса
            date = request.POST.get('date')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            shift_type = request.POST.get('shift_type')
            reason = request.POST.get('reason')
            request_type = request.POST.get('request_type', 'change')  # 'change' или 'day_off'
            
            # Определяем текст уведомления в зависимости от типа запроса
            if request_type == 'day_off':
                # Запрос на выходной
                notification_title = f'Запрос на выходной - {request.user.get_full_name()}'
                notification_message = f'''
Сотрудник {request.user.get_full_name()} запросил выходной:
- Дата: {date}
- Причина: {reason}
                '''
            else:
                # Запрос на изменение смены
                notification_title = f'Запрос на изменение графика - {request.user.get_full_name()}'
                notification_message = f'''
Сотрудник {request.user.get_full_name()} запросил изменение графика:
- Дата: {date}
- Время: {start_time} - {end_time}
- Тип смены: {shift_type}
- Причина: {reason}
                '''
            
            # Получаем всех менеджеров и администраторов для отправки уведомлений
            managers = User.objects.filter(role__in=['manager', 'admin'])
            
            # Создаем уведомления для каждого менеджера
            for manager in managers:
                Notification.objects.create(
                    user=manager,
                    notification_type='schedule_change',
                    title=notification_title,
                    message=notification_message,
                    related_pvz=request.user.pvz.first()
                )
            
            # Перенаправляем на страницу с графиком после успешной отправки
            return redirect('actual_schedule')
            
        except Exception as e:
            print(f"Ошибка при создании запроса: {e}")
            return redirect('actual_schedule')
    
    return redirect('actual_schedule')

# ===== УВЕДОМЛЕНИЯ =====
@login_required
@csrf_exempt
def get_notifications(request):
    """AJAX: Получение уведомлений пользователя"""
    if request.method == 'GET':
        try:
            notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
            notifications_data = []
            
            for notification in notifications:
                notifications_data.append({
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at.strftime('%d.%m.%Y %H:%M'),
                    'pvz_name': notification.related_pvz.pvz_name if notification.related_pvz else ''
                })
            
            unread_count = request.user.unread_notifications_count
            
            return JsonResponse({
                'success': True,
                'notifications': notifications_data,
                'unread_count': unread_count
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@csrf_exempt
def mark_notification_read(request):
    """AJAX: Отметить уведомление как прочитанное"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            notification_id = data.get('notification_id')
            
            if notification_id == 'all':
                # Отмечаем все уведомления как прочитанные
                Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            else:
                # Отмечаем конкретное уведомление как прочитанное
                notification = Notification.objects.get(id=notification_id, user=request.user)
                notification.is_read = True
                notification.save()
            
            unread_count = request.user.unread_notifications_count
            
            return JsonResponse({
                'success': True,
                'unread_count': unread_count
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(admin_required)
def settings(request):
    """Настройки системы (только для админов)"""
    # Здесь можно добавить логику для обработки сохранения настроек
    if request.method == 'POST':
        # Обработка сохранения настроек
        pass
    
    context = {
        'system_settings': {
            'company_name': 'WorkSchedule IS',
            'timezone': 'Europe/Moscow',
            'work_week_start': 'monday',
            'shift_duration': 12,  # Обновили на 12 часов
            'crm_sync_enabled': True,
            'sync_interval': 30,
            'auto_backup': True,
        },
        'backup_files': [
            {'name': 'backup_2025_10_22_1430.sql', 'date': '22.10.2025 14:30', 'size': '2.4 MB'},
            {'name': 'backup_2025_10_21_0300.sql', 'date': '21.10.2025 03:00', 'size': '2.3 MB'},
            {'name': 'backup_2025_10_20_0300.sql', 'date': '20.10.2025 03:00', 'size': '2.3 MB'},
        ],
        'system_logs': [
            {'time': '22.10.2025 14:25:03', 'level': 'info', 'user': 'valeria_bolgar', 'action': 'Просмотр графика', 'details': 'Пользователь просмотрел свой график на октябрь'},
            {'time': '22.10.2025 14:20:15', 'level': 'warning', 'user': 'system', 'action': 'Синхронизация с CRM', 'details': 'Пропущено 2 записи при синхронизации'},
            {'time': '22.10.2025 14:15:42', 'level': 'error', 'user': 'test_admin', 'action': 'Изменение графика', 'details': 'Ошибка валидации данных смены'},
        ]
    }
    return render(request, 'settings.html', context)

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def generate_calendar_days(year, month):
    """Генерирует дни для календаря (заглушка)"""
    days = []
    today = timezone.now().date()
    
    # Пример: 35 дней календаря
    for i in range(35):
        date = today + timedelta(days=i-15)  # Центрируем вокруг сегодняшнего дня
        days.append({
            'date': date,
            'is_today': date == today,
            'is_other_month': date.month != month,
            'shifts': []  # Здесь будут реальные смены из базы
        })
    
    return days

def populate_all_months_data():
    """Заполняет тестовыми данными все месяцы с июня по октябрь"""
    from django.contrib.auth import get_user_model
    from .models import Schedule, PVZ
    from datetime import datetime
    import random
    
    User = get_user_model()
    
    try:
        # Получаем ПВЗ и сотрудников
        pvz = PVZ.objects.get(pvz_name='KSM_28')
        employee1 = User.objects.get(username='valeria_bolgar')
        employee2 = User.objects.get(username='ivan_ivanov')
        
        # Очищаем старые данные
        Schedule.objects.filter(user__in=[employee1, employee2]).delete()
        
        # Данные для каждого месяца
        months_data = {
            6: {'employee1': 13, 'employee2': 12},  # Июнь
            7: {'employee1': 15, 'employee2': 14},  # Июль
            8: {'employee1': 12, 'employee2': 11},  # Август
            9: {'employee1': 14, 'employee2': 13},  # Сентябрь
            10: {'employee1': 8, 'employee2': 8},   # Октябрь
        }
        
        shift_types = ['full', 'half', 'dayoff']
        
        for month, data in months_data.items():
            print(f"Создание данных для месяца {month}...")
            
            # Создаем смены для первого сотрудника
            for i in range(data['employee1']):
                day = random.randint(1, 28)
                shift_type = random.choice(shift_types)
                
                Schedule.objects.create(
                    user=employee1,
                    pvz=pvz,
                    work_date=datetime(2025, month, day).date(),
                    shift_start='09:00',
                    shift_end='21:00',
                    shift_type=shift_type
                )
            
            # Создаем смены для второго сотрудника  
            for i in range(data['employee2']):
                day = random.randint(1, 28)
                shift_type = random.choice(shift_types)
                
                Schedule.objects.create(
                    user=employee2,
                    pvz=pvz,
                    work_date=datetime(2025, month, day).date(),
                    shift_start='09:00',
                    shift_end='21:00',
                    shift_type=shift_type
                )
        
        print("Данные для всех месяцев успешно созданы!")
        return True
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return False


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ =====

@login_required
@user_passes_test(admin_required)
def users(request):
    """Страница управления пользователями для админа"""
    users = User.objects.all().order_by('-date_joined')
    pvz_list = PVZ.objects.all()
    
    context = {
        'users': users,
        'pvz_list': pvz_list
    }
    return render(request, 'users.html', context)

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def add_user(request):
    """Добавление нового пользователя"""
    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            phone = request.POST.get('phone', '').strip()
            role = request.POST.get('role', 'employee')
            pvz_ids = request.POST.getlist('pvz')
            
            # Проверка существующего пользователя
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Пользователь с таким логином уже существует'
                })
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Пользователь с таким email уже существует'
                })
            
            # Создание пользователя
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=make_password(password),
                phone=phone,
                role=role,
                is_staff=role == 'admin',  # Админы получают доступ к админке
                is_superuser=role == 'admin'
            )
            
            # Добавление ПВЗ
            for pvz_id in pvz_ids:
                try:
                    pvz = PVZ.objects.get(id=pvz_id)
                    user.pvz.add(pvz)
                except PVZ.DoesNotExist:
                    continue
            
            return JsonResponse({
                'success': True,
                'message': f'Пользователь {username} успешно создан',
                'user_id': user.id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(admin_required)
def get_user_data(request, user_id):
    """Получение данных пользователя для редактирования"""
    try:
        user = User.objects.get(id=user_id)
        pvz_ids = list(user.pvz.values_list('id', flat=True))
        
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.full_name,
            'phone': user.phone,
            'role': user.role,
            'role_display': user.get_role_display(),
            'is_blocked': user.is_blocked,
            'pvz_ids': pvz_ids,
            'date_joined': user.date_joined.strftime('%d.%m.%Y %H:%M'),
            'last_login': user.last_login.strftime('%d.%m.%Y %H:%M') if user.last_login else None
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def update_user(request, user_id):
    """Обновление данных пользователя"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            
            # Обновление основных полей
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.phone = request.POST.get('phone', '').strip()
            
            # Обновление ПВЗ
            pvz_ids = request.POST.getlist('pvz')
            user.pvz.clear()
            for pvz_id in pvz_ids:
                try:
                    pvz = PVZ.objects.get(id=pvz_id)
                    user.pvz.add(pvz)
                except PVZ.DoesNotExist:
                    continue
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Данные пользователя обновлены'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def toggle_block_user(request, user_id):
    """Блокировка/разблокировка пользователя"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            
            # Нельзя заблокировать самого себя
            if user == request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Нельзя заблокировать самого себя'
                })
            
            user.is_blocked = not user.is_blocked
            user.is_active = not user.is_blocked  # Отключаем возможность входа
            user.save()
            
            action = 'заблокирован' if user.is_blocked else 'разблокирован'
            return JsonResponse({
                'success': True,
                'message': f'Пользователь {action}',
                'is_blocked': user.is_blocked
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def change_user_role(request, user_id):
    """Изменение роли пользователя"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_role = data.get('new_role')
            
            if new_role not in ['admin', 'manager', 'employee']:
                return JsonResponse({
                    'success': False,
                    'error': 'Неверная роль'
                })
            
            user = User.objects.get(id=user_id)
            
            # Проверка на изменение роли самому себе
            if user == request.user and new_role != 'admin':
                return JsonResponse({
                    'success': False,
                    'error': 'Нельзя понизить свою роль'
                })
            
            user.role = new_role
            user.is_staff = new_role == 'admin'
            user.is_superuser = new_role == 'admin'
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Роль пользователя изменена на {user.get_role_display()}',
                'role': user.role,
                'role_display': user.get_role_display()
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def delete_user(request, user_id):
    """Удаление пользователя"""
    if request.method == 'DELETE':
        try:
            user = User.objects.get(id=user_id)
            
            # Нельзя удалить самого себя
            if user == request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Нельзя удалить самого себя'
                })
            
            username = user.username
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Пользователь {username} удален'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def api_update_user(request, user_id):
    """API: Обновление данных пользователя"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            user = User.objects.get(id=user_id)
            
            # Обновляем данные
            if 'first_name' in data:
                user.first_name = data['first_name'].strip()
            if 'last_name' in data:
                user.last_name = data['last_name'].strip()
            if 'email' in data:
                user.email = data['email'].strip()
            if 'phone' in data:
                user.phone = data['phone'].strip()
            
            # Обновляем ПВЗ
            if 'pvz_ids' in data:
                user.pvz.clear()
                for pvz_id in data['pvz_ids']:
                    try:
                        pvz = PVZ.objects.get(id=pvz_id)
                        user.pvz.add(pvz)
                    except PVZ.DoesNotExist:
                        pass
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Данные пользователя обновлены'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@user_passes_test(admin_required)
@csrf_exempt
def api_change_password(request, user_id):
    """API: Изменение пароля пользователя"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_password = data.get('new_password')
            
            if not new_password or len(new_password) < 8:
                return JsonResponse({'success': False, 'error': 'Пароль должен содержать минимум 8 символов'})
            
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Пароль успешно изменен'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

# Добавим в views.py функции для менеджера

@login_required
@user_passes_test(manager_required)
def manager_users(request):
    """Страница управления пользователями для менеджера"""
    # Менеджер видит только сотрудников своих ПВЗ
    manager_pvz = request.user.pvz.all()
    users_list = User.objects.filter(role='employee', pvz__in=manager_pvz).distinct().order_by('last_name', 'first_name')
    
    context = {
        'users': users_list,
        'pvz_list': manager_pvz  # Только ПВЗ менеджера
    }
    return render(request, 'manager_users.html', context)

# API функции для менеджера
@login_required
@user_passes_test(manager_required)
def api_manager_get_user(request, user_id):
    """API: Получение данных пользователя для менеджера"""
    try:
        user = User.objects.get(id=user_id)
        
        # Проверяем, что менеджер может управлять этим пользователем
        manager_pvz = request.user.pvz.all()
        if not (user.role == 'employee' and user.pvz.filter(id__in=manager_pvz).exists()):
            return JsonResponse({'success': False, 'error': 'Нет прав для управления этим пользователем'})
        
        pvz_ids = list(user.pvz.values_list('id', flat=True))
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'role': user.role,
                'role_display': user.get_role_display(),
                'phone': user.phone,
                'is_blocked': user.is_blocked,
                'is_active': user.is_active,
                'pvz_ids': pvz_ids
            }
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пользователь не найден'})

@login_required
@user_passes_test(manager_required)
@csrf_exempt
def api_manager_update_user(request, user_id):
    """API: Обновление данных пользователя менеджером"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            user = User.objects.get(id=user_id)
            
            # Проверяем, что менеджер может управлять этим пользователем
            manager_pvz = request.user.pvz.all()
            if not (user.role == 'employee' and user.pvz.filter(id__in=manager_pvz).exists()):
                return JsonResponse({'success': False, 'error': 'Нет прав для управления этим пользователем'})
            
            # Обновляем данные (только разрешенные поля)
            if 'first_name' in data:
                user.first_name = data['first_name'].strip()
            if 'last_name' in data:
                user.last_name = data['last_name'].strip()
            if 'email' in data:
                user.email = data['email'].strip()
            if 'phone' in data:
                user.phone = data['phone'].strip()
            
            # Обновляем ПВЗ (только ПВЗ менеджера)
            if 'pvz_ids' in data:
                user.pvz.clear()
                for pvz_id in data['pvz_ids']:
                    try:
                        pvz = PVZ.objects.get(id=pvz_id)
                        # Проверяем, что это ПВЗ менеджера
                        if pvz in manager_pvz:
                            user.pvz.add(pvz)
                    except PVZ.DoesNotExist:
                        pass
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Данные сотрудника обновлены'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@user_passes_test(manager_required)
def manager_users(request):
    """Страница управления пользователями для менеджера"""
    # Менеджер видит только сотрудников своих ПВЗ
    manager_pvz = request.user.pvz.all()
    users_list = User.objects.filter(role='employee', pvz__in=manager_pvz).distinct().order_by('last_name', 'first_name')
    
    context = {
        'users': users_list,
        'pvz_list': manager_pvz  # Только ПВЗ менеджера
    }
    return render(request, 'manager_users.html', context)

@login_required
@user_passes_test(manager_required)
@csrf_exempt
def api_manager_add_user(request):
    """API: Добавление нового пользователя менеджером"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            phone = data.get('phone', '').strip()
            password = data.get('password', '').strip()
            pvz_ids = data.get('pvz_ids', [])
            
            # Проверка обязательных полей
            if not username or not email or not password:
                return JsonResponse({'success': False, 'error': 'Заполните обязательные поля'})
            
            # Проверка существующего пользователя
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'error': 'Пользователь с таким логином уже существует'})
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'Пользователь с таким email уже существует'})
            
            # Проверка ПВЗ (только ПВЗ менеджера)
            manager_pvz = request.user.pvz.all()
            valid_pvz_ids = []
            for pvz_id in pvz_ids:
                try:
                    pvz = PVZ.objects.get(id=pvz_id)
                    if pvz in manager_pvz:
                        valid_pvz_ids.append(pvz_id)
                except PVZ.DoesNotExist:
                    pass
            
            # Создание пользователя (только сотрудник, роль фиксированная)
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role='employee',  # Менеджер может создавать только сотрудников
                phone=phone,
                is_staff=False,
                is_superuser=False
            )
            user.set_password(password)
            user.save()
            
            # Добавление ПВЗ
            for pvz_id in valid_pvz_ids:
                try:
                    pvz = PVZ.objects.get(id=pvz_id)
                    user.pvz.add(pvz)
                except PVZ.DoesNotExist:
                    pass
            
            return JsonResponse({
                'success': True,
                'message': f'Сотрудник {username} успешно создан'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@user_passes_test(manager_required)
def generate_orders(request):
    """Генерация заказов за период с предпросмотром"""
    if request.method == 'POST':
        form = OrderGenerationForm(request.POST)
        if form.is_valid():
            try:
                pvz = form.cleaned_data['pvz']
                start_date = form.cleaned_data['date_range_start']
                end_date = form.cleaned_data['date_range_end']
                
                # Генерируем данные
                generated_data = generate_orders_for_period(pvz, start_date, end_date)
                
                # Сохраняем во временную таблицу
                temp_data = TemporaryOrderData.objects.create(
                    pvz=pvz,
                    date_range_start=start_date,
                    date_range_end=end_date,
                    generated_data=generated_data,
                    preview_data=generate_preview_text(generated_data),
                    created_by=request.user,
                    status='generated'
                )
                
                # Сохраняем в файл для предпросмотра
                file_path = save_to_excel(temp_data)
                temp_data.file_path = file_path
                temp_data.save()
                
                messages.success(
                    request,
                    f'Данные успешно сгенерированы для ПВЗ {pvz.pvz_name} '
                    f'за период с {start_date.strftime("%d.%m.%Y")} по {end_date.strftime("%d.%m.%Y")}. '
                    f'Всего дней: {(end_date - start_date).days + 1}'
                )
                
                # Редирект на страницу предпросмотра
                return redirect('preview_orders', temp_id=temp_data.id)
                
            except Exception as e:
                messages.error(request, f'Ошибка при генерации данных: {str(e)}')
    else:
        form = OrderGenerationForm()
    
    context = {
        'form': form,
        'existing_temps': TemporaryOrderData.objects.filter(
            created_by=request.user,
            status='generated'
        ).order_by('-created_at')[:5]
    }
    return render(request, 'generate_orders.html', context)


def generate_orders_for_period(pvz, start_date, end_date):
    """Генерация заказов за период"""
    all_orders = []
    current_date = start_date
    
    while current_date <= end_date:
        # Генерируем данные для одного дня
        day_data = generate_daily_orders(pvz, current_date)
        all_orders.extend(day_data)
        current_date += timedelta(days=1)
    
    return all_orders


def generate_daily_orders(pvz, date):
    """Генерация заказов на один день"""
    orders = []
    
    # Разные шаблоны для разных дней недели
    weekday = date.weekday()  # 0 - понедельник, 6 - воскресенье
    
    if weekday in [5, 6]:  # Суббота, воскресенье
        hourly_template = {
            9: random.randint(5, 15),
            10: random.randint(10, 20),
            11: random.randint(15, 25),
            12: random.randint(20, 30),
            13: random.randint(25, 35),
            14: random.randint(20, 30),
            15: random.randint(15, 25),
            16: random.randint(20, 30),
            17: random.randint(25, 35),
            18: random.randint(15, 25),
            19: random.randint(10, 20),
            20: random.randint(5, 15)
        }
    else:  # Будни
        hourly_template = {
            9: random.randint(8, 18),
            10: random.randint(12, 22),
            11: random.randint(10, 20),
            12: random.randint(25, 35),
            13: random.randint(30, 40),
            14: random.randint(15, 25),
            15: random.randint(20, 30),
            16: random.randint(25, 35),
            17: random.randint(30, 40),
            18: random.randint(20, 30),
            19: random.randint(12, 22),
            20: random.randint(8, 18)
        }
    
    for hour, count in hourly_template.items():
        for _ in range(count):
            order_time = generate_random_time_in_hour(hour)
            order_number = generate_order_number()
            client_id = generate_client_id(order_number)
            
            orders.append({
                'date': date.strftime('%Y-%m-%d'),
                'time': order_time.strftime('%H:%M:%S'),
                'order_number': order_number,
                'client_id': client_id,
                'hour': hour
            })
    
    return orders


def save_to_excel(temp_data):
    """Сохранение во временный Excel файл"""
    if not PANDAS_AVAILABLE:
        raise ImportError("Pandas не установлен. Установите его через 'pip install pandas openpyxl'")
    
    # Создаем папку для временных файлов
    temp_dir = os.path.join('media', 'temp_orders')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Создаем имя файла
    filename = f'temp_orders_{temp_data.pvz.pvz_name}_{temp_data.date_range_start}_{temp_data.date_range_end}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    file_path = os.path.join(temp_dir, filename)
    
    # Создаем DataFrame
    orders_data = temp_data.generated_data
    df = pd.DataFrame(orders_data)
    
    # Сохраняем в Excel
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Заказы', index=False)
        
        # Добавляем сводную статистику
        summary_df = generate_summary(df)
        summary_df.to_excel(writer, sheet_name='Статистика', index=False)
    
    return file_path

def generate_summary(df):
    """Генерация сводной статистики"""
    if not PANDAS_AVAILABLE:
        return None
    
    df['date'] = pd.to_datetime(df['date'])
    summary = df.groupby(df['date'].dt.date).agg({
        'order_number': 'count',
        'hour': lambda x: x.value_counts().index[0] if not x.empty else 0  # Самый загруженный час
    }).reset_index()
    
    summary.columns = ['Дата', 'Количество заказов', 'Пиковый час']
    return summary

def generate_summary(df):
    """Генерация сводной статистики"""
    df['date'] = pd.to_datetime(df['date'])
    summary = df.groupby(df['date'].dt.date).agg({
        'order_number': 'count',
        'hour': lambda x: x.value_counts().index[0]  # Самый загруженный час
    }).reset_index()
    
    summary.columns = ['Дата', 'Количество заказов', 'Пиковый час']
    return summary

def generate_preview_text(data):
    """Генерация текста для предпросмотра"""
    if not data:
        return "Нет данных"
    
    # Группируем по дате
    date_counts = {}
    for order in data:
        date = order['date']
        date_counts[date] = date_counts.get(date, 0) + 1
    
    preview_lines = []
    for date, count in sorted(date_counts.items()):
        preview_lines.append(f"{date}: {count} заказов")
    
    return "\n".join(preview_lines)

@login_required
@user_passes_test(manager_required)
def preview_orders(request, temp_id):
    """Страница предпросмотра сгенерированных данных"""
    try:
        temp_data = TemporaryOrderData.objects.get(id=temp_id, created_by=request.user)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'import':
                # Импорт данных в основную БД
                imported_count = import_to_database(temp_data)
                temp_data.status = 'imported'
                temp_data.imported_at = timezone.now()
                temp_data.save()
                
                messages.success(request, f'Успешно импортировано {imported_count} заказов в базу данных')
                return redirect('statistics')
            
            elif action == 'reject':
                temp_data.status = 'rejected'
                temp_data.save()
                messages.info(request, 'Данные отклонены и удалены')
                return redirect('generate_orders')
            
            elif action == 'regenerate':
                # Регенерируем данные
                new_data = generate_orders_for_period(
                    temp_data.pvz,
                    temp_data.date_range_start,
                    temp_data.date_range_end
                )
                temp_data.generated_data = new_data
                temp_data.preview_data = generate_preview_text(new_data)
                temp_data.save()
                
                # Обновляем файл
                if temp_data.file_path and os.path.exists(temp_data.file_path):
                    os.remove(temp_data.file_path)
                new_file_path = save_to_excel(temp_data)
                temp_data.file_path = new_file_path
                temp_data.save()
                
                messages.info(request, 'Данные успешно перегенерированы')
                return redirect('preview_orders', temp_id=temp_data.id)
        
        context = {
            'temp_data': temp_data,
            'orders_data': temp_data.generated_data[:100],  # Показываем первые 100 для предпросмотра
            'total_orders': len(temp_data.generated_data),
            'date_range': f"{temp_data.date_range_start.strftime('%d.%m.%Y')} - {temp_data.date_range_end.strftime('%d.%m.%Y')}",
            'days_count': (temp_data.date_range_end - temp_data.date_range_start).days + 1,
            'file_exists': os.path.exists(temp_data.file_path) if temp_data.file_path else False
        }
        return render(request, 'preview_orders.html', context)
        
    except TemporaryOrderData.DoesNotExist:
        messages.error(request, 'Данные не найдены')
        return redirect('generate_orders')

def import_to_database(temp_data):
    """Импорт данных в основную базу данных"""
    imported_count = 0
    
    with transaction.atomic():
        # Сначала группируем по дате для статистики
        date_stats = {}
        
        for order in temp_data.generated_data:
            date = datetime.strptime(order['date'], '%Y-%m-%d').date()
            hour = order['hour']
            
            if date not in date_stats:
                date_stats[date] = {h: 0 for h in range(9, 21)}
            date_stats[date][hour] = date_stats[date].get(hour, 0) + 1
            
            # Создаем детальную запись заказа
            OrderDetail.objects.create(
                pvz=temp_data.pvz,
                order_date=date,
                order_time=datetime.strptime(order['time'], '%H:%M:%S').time(),
                order_number=order['order_number'],
                client_id=order['client_id'],
            )
            imported_count += 1
        
        # Создаем статистические записи
        for date, hourly_counts in date_stats.items():
            OrderStat.objects.update_or_create(
                pvz=temp_data.pvz,
                order_date=date,
                defaults={
                    'hour_9': hourly_counts.get(9, 0),
                    'hour_10': hourly_counts.get(10, 0),
                    'hour_11': hourly_counts.get(11, 0),
                    'hour_12': hourly_counts.get(12, 0),
                    'hour_13': hourly_counts.get(13, 0),
                    'hour_14': hourly_counts.get(14, 0),
                    'hour_15': hourly_counts.get(15, 0),
                    'hour_16': hourly_counts.get(16, 0),
                    'hour_17': hourly_counts.get(17, 0),
                    'hour_18': hourly_counts.get(18, 0),
                    'hour_19': hourly_counts.get(19, 0),
                    'hour_20': hourly_counts.get(20, 0),
                }
            )
    
    return imported_count

@login_required
@user_passes_test(manager_required)
def download_temp_file(request, temp_id):
    """Скачивание временного файла"""
    try:
        temp_data = TemporaryOrderData.objects.get(id=temp_id, created_by=request.user)
        
        if temp_data.file_path and os.path.exists(temp_data.file_path):
            with open(temp_data.file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="orders_{temp_data.pvz.pvz_name}_{temp_data.date_range_start}_{temp_data.date_range_end}.xlsx"'
                return response
        
        messages.error(request, 'Файл не найден')
        return redirect('preview_orders', temp_id=temp_id)
        
    except TemporaryOrderData.DoesNotExist:
        messages.error(request, 'Данные не найдены')
        return redirect('generate_orders')

def generate_order_details(pvz, target_date, distribution):
    """Генерация деталей заказов"""
    orders_created = 0
    
    # Удаляем старые заказы для этой даты и ПВЗ
    OrderDetail.objects.filter(pvz=pvz, order_date=target_date).delete()
    
    with transaction.atomic():
        for hour, count in distribution.items():
            if count <= 0:
                continue
                
            # Генерируем времена для заказов в этом часу
            for i in range(count):
                # Генерируем случайное время в пределах часа
                order_time = generate_random_time_in_hour(hour)
                
                # Генерируем номер заказа
                order_number = generate_order_number()
                client_id = generate_client_id(order_number)
                
                # Создаем деталь заказа
                OrderDetail.objects.create(
                    pvz=pvz,
                    order_date=target_date,
                    order_time=order_time,
                    order_number=order_number,
                    client_id=client_id,
                )
                
                orders_created += 1
    
    return orders_created

def generate_random_time_in_hour(hour):
    """Генерация случайного времени в пределах указанного часа"""
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime.strptime(f"{hour:02d}:{minute:02d}:{second:02d}", "%H:%M:%S").time()

def generate_order_number():
    """Генерация номера заказа"""
    return f"{random.randint(10000000, 99999999):08d}-{random.randint(1000, 9999):04d}"

def generate_client_id(order_number):
    """Генерация ID клиента из номера заказа"""
    client_id = order_number.split('-')[0]
    if len(client_id) == 10 and client_id.startswith('0'):
        client_id = client_id[1:]
    return client_id

def calculate_break_times(hourly_data):
    """Рассчитать рекомендуемое время для перерывов"""
    recommendations = []
    
    # Ищем периоды с низкой нагрузкой
    for i in range(len(hourly_data) - 1):  # -1 чтобы не выйти за границы
        current_hour = hourly_data[i]
        next_hour = hourly_data[i + 1]
        
        # Если в обоих часах низкая нагрузка (менее 15 заказов в час)
        if current_hour['order_count'] < 15 and next_hour['order_count'] < 15:
            # Рекомендуем перерыв в конце первого часа
            break_time = f"{current_hour['hour']}:45-{current_hour['hour']+1}:00"
            
            # Определяем тип нагрузки
            avg_orders = (current_hour['order_count'] + next_hour['order_count']) / 2
            if avg_orders < 10:
                load_type = 'good'  # низкая нагрузка
            elif avg_orders < 20:
                load_type = 'average'  # средняя нагрузка
            else:
                load_type = 'bad'  # высокая нагрузка
            
            recommendations.append({
                'time': break_time,
                'load_type': load_type,
                'description': 'Низкая нагрузка' if load_type == 'good' else 'Средняя нагрузка' if load_type == 'average' else 'Высокая нагрузка'
            })
    
    # Если нет рекомендаций, добавляем стандартные
    if not recommendations:
        recommendations = [
            {'time': '11:00-11:15', 'load_type': 'good', 'description': 'Низкая нагрузка'},
            {'time': '14:30-14:45', 'load_type': 'good', 'description': 'Низкая нагрузка'},
            {'time': '15:45-16:00', 'load_type': 'average', 'description': 'Средняя нагрузка'},
            {'time': '19:15-19:30', 'load_type': 'good', 'description': 'Низкая нагрузка'},
        ]
    
    return recommendations[:4]  # Возвращаем не более 4 рекомендаций

@login_required
@user_passes_test(manager_required)
def clear_orders(request):
    """Очистка заказов для выбранного ПВЗ и даты"""
    if request.method == 'POST':
        pvz_id = request.POST.get('pvz_id')
        date_str = request.POST.get('date')
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            pvz = PVZ.objects.get(id=pvz_id)
            
            # Удаляем статистику и детали
            stat_deleted, _ = OrderStat.objects.filter(pvz=pvz, order_date=date).delete()
            detail_deleted, _ = OrderDetail.objects.filter(pvz=pvz, order_date=date).delete()
            
            messages.success(
                request, 
                f'Удалено статистических записей: {stat_deleted}, детальных заказов: {detail_deleted} '
                f'для ПВЗ {pvz.pvz_name} на {date.strftime("%d.%m.%Y")}'
            )
            
        except Exception as e:
            messages.error(request, f'Ошибка при удалении заказов: {str(e)}')
    
    return redirect('statistics')

@login_required
@user_passes_test(manager_required)
def statistics(request):
    """Страница статистики с реальными данными"""
    pvz_list = PVZ.objects.all()
    employees = User.objects.filter(role='employee').prefetch_related('pvz')
    
    # Получаем выбранный ПВЗ
    selected_pvz_id = request.GET.get('pvz_id')
    selected_date_str = request.GET.get('date')
    
    if selected_pvz_id:
        try:
            selected_pvz = PVZ.objects.get(id=selected_pvz_id)
        except PVZ.DoesNotExist:
            selected_pvz = None
    else:
        selected_pvz = None
    
    # Определяем дату
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = datetime.now().date()
    else:
        selected_date = datetime.now().date()
    
    # Данные для прогноза (последние 5 дней)
    forecast_dates = []
    
    for i in range(-2, 3):  # 2 дня назад, сегодня, 2 дня вперед
        forecast_date = selected_date + timedelta(days=i)
        
        # Получаем статистику за этот день
        if selected_pvz:
            order_stat = OrderStat.objects.filter(pvz=selected_pvz, order_date=forecast_date).first()
            orders_for_date = order_stat.total_orders if order_stat else 0
        else:
            # Если не выбран ПВЗ - сумма по всем ПВЗ
            order_stats = OrderStat.objects.filter(order_date=forecast_date)
            orders_for_date = sum(stat.total_orders for stat in order_stats) if order_stats else 0
        
        forecast_dates.append({
            'date': forecast_date,
            'formatted_date': forecast_date.strftime('%d.%m.%Y'),
            'day_name': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 
                        'Суббота', 'Воскресенье'][forecast_date.weekday()],
            'orders': orders_for_date,
            'is_today': forecast_date == datetime.now().date(),
            'is_past': forecast_date < datetime.now().date(),
            'is_future': forecast_date > datetime.now().date(),
        })
    
    # Детальный прогноз на выбранную дату
    detailed_forecast = []
    chart_height = 250  # Высота диаграммы в пикселях
    
    if selected_pvz:
        order_stat = OrderStat.objects.filter(pvz=selected_pvz, order_date=selected_date).first()
        
        if order_stat:
            # Создаем словарь данных по часам
            hourly_data = {
                9: order_stat.hour_9,
                10: order_stat.hour_10,
                11: order_stat.hour_11,
                12: order_stat.hour_12,
                13: order_stat.hour_13,
                14: order_stat.hour_14,
                15: order_stat.hour_15,
                16: order_stat.hour_16,
                17: order_stat.hour_17,
                18: order_stat.hour_18,
                19: order_stat.hour_19,
                20: order_stat.hour_20,
            }
            
            # Находим максимальное количество заказов
            max_order_count = max(hourly_data.values())
            
            # Если нет данных, устанавливаем дефолт
            if max_order_count == 0:
                max_order_count = 1
            
            # Подготавливаем данные для отображения
            for hour in range(9, 21):
                time_range = f"{hour:02d}:00-{hour+1:02d}:00"
                order_count = hourly_data.get(hour, 0)
                
                # Рассчитываем высоту столбца в пикселях
                if max_order_count > 0:
                    height_px = int((order_count / max_order_count) * chart_height)
                else:
                    height_px = 0
                
                # Устанавливаем минимальную высоту для видимости
                if order_count > 0 and height_px < 5:
                    height_px = 5
                
                # Определяем, является ли час пиковым
                is_peak = order_count >= (max_order_count * 0.7)  # пиковый час - 70% от максимума
                
                detailed_forecast.append({
                    'hour': hour,
                    'time_range': time_range,
                    'order_count': order_count,
                    'height_px': height_px,
                    'is_peak': is_peak,
                })
        else:
            # Если нет данных
            for hour in range(9, 21):
                detailed_forecast.append({
                    'hour': hour,
                    'time_range': f"{hour:02d}:00-{hour+1:02d}:00",
                    'order_count': 0,
                    'height_px': 0,
                    'is_peak': False,
                })
    else:
        # Заполняем пустыми данными
        for hour in range(9, 21):
            detailed_forecast.append({
                'hour': hour,
                'time_range': f"{hour:02d}:00-{hour+1:02d}:00",
                'order_count': 0,
                'height_px': 0,
                'is_peak': False,
            })
    
    # Создаем значения для оси Y
    y_axis_values = []
    step = 10
    
    # Находим максимальное количество заказов из detailed_forecast
    max_order_count_in_data = max([item['order_count'] for item in detailed_forecast])
    
    if max_order_count_in_data <= 0:
        max_value = step
    else:
        # Округляем вверх до ближайшего кратного step
        max_value = ((max_order_count_in_data // step) + 1) * step
    
    # Создаем значения от 0 до max_value с шагом step
    for value in range(0, max_value + step, step):
        y_axis_values.append(value)
    
    # Переворачиваем для правильного отображения сверху вниз
    y_axis_values = list(reversed(y_axis_values))
    
    # Рассчитываем позиции для сетки (в пикселях)
    grid_positions = []
    for value in y_axis_values:
        if value > 0:
            position_px = int((value / max_value) * chart_height) if max_value > 0 else 0
            grid_positions.append({
                'value': value,
                'position_px': position_px
            })
    
    # Рассчитываем рекомендации по перерывам
    break_recommendations = calculate_break_times(detailed_forecast)
    
    # Общее количество заказов на выбранную дату
    total_orders_today = sum([item['order_count'] for item in detailed_forecast])
    
    context = {
        'pvz_list': pvz_list,
        'employees': employees,
        'selected_pvz': selected_pvz,
        'selected_date': selected_date,
        'forecast_dates': forecast_dates,
        'detailed_forecast': detailed_forecast,
        'break_recommendations': break_recommendations,
        'total_orders_today': total_orders_today,
        'y_axis_values': y_axis_values,
        'max_y_value': max_value,
        'grid_positions': grid_positions,
        'chart_height': chart_height,
    }
    return render(request, 'statistics.html', context)