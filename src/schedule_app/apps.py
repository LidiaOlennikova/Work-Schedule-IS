from django.apps import AppConfig

class ScheduleAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedule_app'
    
    def ready(self):
        try:
            import schedule_app.signals
        except ImportError:
            # Игнорируем ошибку при создании миграций
            pass