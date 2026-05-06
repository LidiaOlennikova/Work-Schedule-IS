from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.hashers import make_password

class User(AbstractUser):
    ROLE_CHOICES = [
        ('employee', 'Сотрудник'),
        ('manager', 'Управляющий'),
        ('admin', 'Администратор'),
    ]

    worked_hours = models.IntegerField(default=0, verbose_name='Отработано часов')
    late_count = models.IntegerField(default=0, verbose_name='Количество опозданий')
    overtime_count = models.IntegerField(default=0, verbose_name='Количество переработок')
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    pvz = models.ManyToManyField('PVZ', blank=True, related_name='users')
    phone = models.CharField(max_length=20, blank=True)
    is_blocked = models.BooleanField(default=False, verbose_name='Заблокирован')
    is_online = models.BooleanField(default=False, verbose_name='Онлайн')
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name='Последняя активность')

    @property
    def unread_notifications_count(self):
        """Количество непрочитанных уведомлений"""
        return self.notifications.filter(is_read=False).count()
    
    @property
    def full_name(self):
        """Полное имя пользователя"""
        name_parts = []
        if self.first_name:
            name_parts.append(self.first_name)
        if self.last_name:
            name_parts.append(self.last_name)
        return ' '.join(name_parts) if name_parts else self.username
    
    def get_role_display(self):
        """Отображаемое значение роли"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    def get_status_display(self):
        """Статус пользователя"""
        if self.is_blocked:
            return "Заблокирован"
        elif not self.is_active:
            return "Неактивен"
        else:
            return "Активен"
    
    def can_be_managed_by(self, manager):
        """Может ли пользователь управляться данным менеджером"""
        if manager.role == 'admin':
            return True
        elif manager.role == 'manager':
            # Менеджер может управлять сотрудниками своих ПВЗ
            return self.role == 'employee' and self.pvz.filter(id__in=manager.pvz.all()).exists()
        return False

class PVZ(models.Model):
    pvz_name = models.CharField(max_length=100)
    pvz_work_schedule = models.CharField(max_length=100) 
    pvz_contact_info = models.TextField()

    def __str__(self):
        return self.pvz_name

class Schedule(models.Model):
    SHIFT_TYPES = [
        ('full', 'Полная смена'),
        ('half', 'Половина смены'),
        ('day_off', 'Выходной'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pvz = models.ForeignKey(PVZ, on_delete=models.CASCADE)
    work_date = models.DateField()
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPES)
    
    def get_shift_type_display(self):
        """Возвращает отображаемое значение типа смены"""
        shift_display = {
            'full': 'Р',
            'half': 'Р 1/2', 
            'day_off': 'В'
        }
        return shift_display.get(self.shift_type, '')
    
    def __str__(self):
        return f"{self.user.username} - {self.work_date} - {self.get_shift_type_display()}"

class LoginAudit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='Время входа')
    ip_address = models.GenericIPAddressField(verbose_name='IP адрес')
    user_agent = models.TextField(verbose_name='User Agent')
    success = models.BooleanField(default=True, verbose_name='Успешный вход')
    
    class Meta:
        verbose_name = 'Запись аудита входа'
        verbose_name_plural = 'Журнал аудита входов'
        ordering = ['-login_time']
    
    def __str__(self):
        status = "успешный" if self.success else "неудачный"
        return f"{self.user.username} - {self.login_time} ({status})"

class Feedback(models.Model):
    pvz = models.ForeignKey(PVZ, on_delete=models.CASCADE, verbose_name='ПВЗ')
    client_id = models.CharField(max_length=50, verbose_name='ID клиента')
    
    # Критерии для сотрудников ПВЗ (1-3)
    service_speed = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Скорость обслуживания в ПВЗ',
        null=True,
        blank=True
    )
    employee_politeness = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Вежливость сотрудника ПВЗ',
        null=True,
        blank=True
    )
    employee_competence = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Компетентность сотрудника ПВЗ',
        null=True,
        blank=True
    )
    
    # Критерии для ПВЗ (4-5)
    cleanliness = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Чистота ПВЗ',
        null=True,
        blank=True
    )
    convenient_location = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Удобное расположение ПВЗ',
        null=True,
        blank=True
    )
    
    feedback_text = models.TextField(verbose_name='Текст отзыва')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    manager_comment = models.TextField(blank=True, verbose_name='Комментарий менеджера')
    
    @property
    def overall_rating_pvz(self):
        """Общий рейтинг ПВЗ (среднее всех 5 критериев)"""
        ratings = [
            self.service_speed,
            self.employee_politeness,
            self.employee_competence,
            self.cleanliness,
            self.convenient_location,
        ]
        
        # Фильтруем None значения
        valid_ratings = [r for r in ratings if r is not None]
        
        if not valid_ratings:
            return 0
        return sum(valid_ratings) / len(valid_ratings)
    
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Отзыв {self.client_id} - {self.overall_rating_pvz:.1f}★"

class EmployeeRating(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Сотрудник', related_name='ratings')
    cleanliness = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Чистота'
    )
    service_speed = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Скорость обслуживания'
    )
    politeness = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Вежливость'
    )
    competence = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Компетентность'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата оценки')
    
    @property
    def overall_rating(self):
        """Исправленный метод для вычисления общего рейтинга"""
        try:
            # Проверяем, что все поля не None
            if (self.cleanliness is None or self.service_speed is None or 
                self.politeness is None or self.competence is None):
                return 0
                
            return (self.cleanliness + self.service_speed + self.politeness + self.competence) / 4
        except (TypeError, AttributeError):
            return 0
    
    class Meta:
        verbose_name = 'Оценка сотрудника'
        verbose_name_plural = 'Оценки сотрудников'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Оценка {self.employee.username} - {self.overall_rating:.1f}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('schedule_change', 'Изменение графика'),
        ('system', 'Системное уведомление'),
        ('feedback', 'Новый отзыв'),
        ('rating', 'Новая оценка'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name='Тип уведомления')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Сообщение')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    related_pvz = models.ForeignKey(PVZ, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Связанный ПВЗ')
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
class GeneratedOrder(models.Model):
    pvz = models.ForeignKey(PVZ, on_delete=models.CASCADE, verbose_name='ПВЗ')
    order_number = models.CharField(max_length=50, verbose_name='Номер заказа')
    client_id = models.CharField(max_length=50, verbose_name='ID клиента')
    issue_time = models.TimeField(verbose_name='Время выдачи')
    issue_date = models.DateField(verbose_name='Дата выдачи')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Сгенерированный заказ'
        verbose_name_plural = 'Сгенерированные заказы'

class OrderStat(models.Model):
    """Статистика заказов по дням и часам"""
    pvz = models.ForeignKey(PVZ, on_delete=models.CASCADE, verbose_name='ПВЗ')
    order_date = models.DateField(verbose_name='Дата заказов')
    hour_9 = models.IntegerField(default=0, verbose_name='09:00-10:00')
    hour_10 = models.IntegerField(default=0, verbose_name='10:00-11:00')
    hour_11 = models.IntegerField(default=0, verbose_name='11:00-12:00')
    hour_12 = models.IntegerField(default=0, verbose_name='12:00-13:00')
    hour_13 = models.IntegerField(default=0, verbose_name='13:00-14:00')
    hour_14 = models.IntegerField(default=0, verbose_name='14:00-15:00')
    hour_15 = models.IntegerField(default=0, verbose_name='15:00-16:00')
    hour_16 = models.IntegerField(default=0, verbose_name='16:00-17:00')
    hour_17 = models.IntegerField(default=0, verbose_name='17:00-18:00')
    hour_18 = models.IntegerField(default=0, verbose_name='18:00-19:00')
    hour_19 = models.IntegerField(default=0, verbose_name='19:00-20:00')
    hour_20 = models.IntegerField(default=0, verbose_name='20:00-21:00')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        unique_together = ['pvz', 'order_date']
    
    @property
    def total_orders(self):
        return sum([
            self.hour_9, self.hour_10, self.hour_11, self.hour_12,
            self.hour_13, self.hour_14, self.hour_15, self.hour_16,
            self.hour_17, self.hour_18, self.hour_19, self.hour_20
        ])

class OrderDetail(models.Model):
    """Детальная информация о сгенерированных заказах"""
    pvz = models.ForeignKey(PVZ, on_delete=models.CASCADE, verbose_name='ПВЗ')
    order_date = models.DateField(verbose_name='Дата заказа')
    order_time = models.TimeField(verbose_name='Время заказа')
    order_number = models.CharField(max_length=50, verbose_name='Номер заказа')
    client_id = models.CharField(max_length=50, verbose_name='ID клиента')
    tracking_number = models.CharField(max_length=100, verbose_name='Трек номер')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

class TemporaryOrderData(models.Model):
    """Временное хранение сгенерированных данных перед загрузкой в БД"""
    pvz = models.ForeignKey(PVZ, on_delete=models.CASCADE, verbose_name='ПВЗ')
    date_range_start = models.DateField(verbose_name='Начало периода')
    date_range_end = models.DateField(verbose_name='Конец периода')
    generated_data = models.JSONField(verbose_name='Сгенерированные данные')
    file_path = models.CharField(max_length=500, verbose_name='Путь к файлу', blank=True)
    preview_data = models.TextField(verbose_name='Предпросмотр данных', blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('generated', 'Сгенерировано'),
            ('approved', 'Подтверждено'),
            ('imported', 'Импортировано'),
            ('rejected', 'Отклонено')
        ],
        default='generated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Временные данные заказов'
        verbose_name_plural = 'Временные данные заказов'
        ordering = ['-created_at']



class Task(models.Model):
    """Модель для управления задачами"""
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнено'),
        ('cancelled', 'Отменено'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Название задачи')
    description = models.TextField(blank=True, verbose_name='Описание')
    pvz = models.ForeignKey('PVZ', on_delete=models.CASCADE, verbose_name='ПВЗ', related_name='tasks')
    assigned_to = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='Назначена сотруднику',
        related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name='Создал',
        related_name='created_tasks'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name='Приоритет')
    deadline = models.DateField(null=True, blank=True, verbose_name='Срок выполнения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлена')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Выполнена')
    is_global = models.BooleanField(default=False, verbose_name='Общая задача на ПВЗ')
    
    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pvz', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['deadline']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def complete(self, user=None):
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        if self.created_by and user and self.created_by != user:
            Notification.objects.create(
                user=self.created_by,
                notification_type='system',
                title=f'Задача выполнена',
                message=f'Сотрудник {user.get_full_name()} выполнил задачу "{self.title}" в ПВЗ {self.pvz.pvz_name}',
                related_pvz=self.pvz
            )
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.deadline and self.status != 'completed':
            return self.deadline < timezone.now().date()
        return False