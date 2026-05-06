from django.test import TestCase
from django.contrib.auth import get_user_model
from django.test import Client
from datetime import date, timedelta
import time

User = get_user_model()


class SystemTests(TestCase):
    """Системные тесты WorkSchedule IS"""
    
    def setUp(self):
        """Настройка перед тестами"""
        self.client = Client()
        self.timestamp = int(time.time())
        
    def test_01_user_creation(self):
        """Тест создания пользователей разных ролей"""
        print("\n1. Тест создания пользователей...")
        
        # Создаем пользователей всех ролей
        employee = User.objects.create_user(
            username=f'employee_{self.timestamp}',
            password='EmployeePass123!',
            email=f'employee_{self.timestamp}@test.com',
            role='employee'
        )
        self.assertEqual(employee.role, 'employee')
        print(f"✅ Создан сотрудник: {employee.username}")
        
        manager = User.objects.create_user(
            username=f'manager_{self.timestamp}',
            password='ManagerPass123!',
            email=f'manager_{self.timestamp}@test.com',
            role='manager'
        )
        self.assertEqual(manager.role, 'manager')
        print(f"✅ Создан менеджер: {manager.username}")
        
        admin = User.objects.create_user(
            username=f'admin_{self.timestamp}',
            password='AdminPass123!',
            email=f'admin_{self.timestamp}@test.com',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.assertEqual(admin.role, 'admin')
        print(f"✅ Создан администратор: {admin.username}")
        
        return employee, manager, admin
    
    def test_02_page_access(self):
        """Тест доступности страниц"""
        print("\n2. Тест доступности страниц...")
        
        # Проверяем публичные страницы
        public_pages = [
            ('/', 'Главная'),
            ('/login/', 'Вход'),
        ]
        
        for url, name in public_pages:
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 302])
            print(f"   {name}: {response.status_code}")
    
    def test_03_authentication(self):
        """Тест аутентификации"""
        print("\n3. Тест аутентификации...")
        
        user = User.objects.create_user(
            username=f'auth_test_{self.timestamp}',
            password='AuthPass123!',
            email=f'auth_{self.timestamp}@test.com',
            role='employee'
        )
        
        # Тестируем логин
        login_success = self.client.login(
            username=f'auth_test_{self.timestamp}',
            password='AuthPass123!'
        )
        self.assertTrue(login_success)
        print(f"✅ Аутентификация успешна")
        
        # Проверяем доступ к профилю
        response = self.client.get('/profile/')
        self.assertIn(response.status_code, [200, 302])
        print(f"✅ Доступ к профилю: {response.status_code}")
    
    def test_04_models_functionality(self):
        """Тест функционала моделей"""
        print("\n4. Тест функционала моделей...")
        
        try:
            from schedule_app.models import PVZ, Schedule
            
            # Создаем ПВЗ
            pvz = PVZ.objects.create(
                pvz_name=f'Тестовый ПВЗ {self.timestamp}',
                pvz_work_schedule='09:00-21:00',
                pvz_contact_info=f'test_{self.timestamp}@pvz.com'
            )
            self.assertEqual(pvz.pvz_name, f'Тестовый ПВЗ {self.timestamp}')
            print(f"✅ Создан ПВЗ: {pvz.pvz_name}")
            
            # Создаем пользователя и смену
            user = User.objects.create_user(
                username=f'schedule_user_{self.timestamp}',
                password='SchedulePass123!',
                email=f'schedule_{self.timestamp}@test.com',
                role='employee'
            )
            
            schedule = Schedule.objects.create(
                user=user,
                pvz=pvz,
                work_date=date.today() + timedelta(days=7),
                shift_start='09:00',
                shift_end='21:00',
                shift_type='full'
            )
            self.assertEqual(schedule.shift_type, 'full')
            print(f"✅ Создана смена на {schedule.work_date}")
            
        except ImportError:
            self.skipTest("Модели не найдены")
    
    def test_05_role_based_access(self):
        """Тест разграничения доступа по ролям"""
        print("\n5. Тест разграничения доступа...")
        
        # Создаем пользователей
        employee = User.objects.create_user(
            username=f'employee_access_{self.timestamp}',
            password='EmployeePass123!',
            email=f'employee_access_{self.timestamp}@test.com',
            role='employee'
        )
        
        manager = User.objects.create_user(
            username=f'manager_access_{self.timestamp}',
            password='ManagerPass123!',
            email=f'manager_access_{self.timestamp}@test.com',
            role='manager'
        )
        
        # Тестируем доступ сотрудника
        self.client.force_login(employee)
        response = self.client.get('/actual-schedule/')
        self.assertIn(response.status_code, [200, 302])
        print(f"✅ Сотрудник может получить график: {response.status_code}")
        
        # Сотрудник не должен иметь доступ к статистике
        response = self.client.get('/statistics/')
        self.assertNotEqual(response.status_code, 200)
        print(f"✅ Сотрудник не имеет доступа к статистике: {response.status_code}")
        
        # Менеджер должен иметь доступ к статистике
        self.client.force_login(manager)
        response = self.client.get('/statistics/')
        self.assertIn(response.status_code, [200, 302])
        print(f"✅ Менеджер имеет доступ к статистике: {response.status_code}")


def run_all_tests():
    """Запуск всех тестов"""
    import unittest
    
    print("="*60)
    print("ЗАПУСК ТЕСТОВ WORKSCHEDULE IS")
    print("="*60)
    
    # Загружаем тесты
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(SystemTests)
    
    # Запускаем
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Выводим результаты
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    print(f"Всего тестов: {result.testsRun}")
    print(f"Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Провалено: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")
    
    return result


if __name__ == '__main__':
    # Этот код работает только при запуске через manage.py test
    print("Запуск тестов через Django test runner...")
    run_all_tests()