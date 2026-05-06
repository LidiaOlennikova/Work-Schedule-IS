from django import forms
from .models import PVZ, Feedback, Task
from datetime import datetime

# Форма для админки Feedback
class FeedbackAdminForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = '__all__'
        widgets = {
            'service_speed': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'employee_politeness': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'employee_competence': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'cleanliness': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'convenient_location': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
        }

# Форма для генерации заказов
class OrderGenerationForm(forms.Form):
    target_date = forms.DateField(
        label='Дата',
        widget=forms.SelectDateWidget(years=range(2024, 2027))
    )
    
    pvz = forms.ModelChoiceField(
        label='Пункт выдачи',
        queryset=PVZ.objects.all(),
        empty_label="Выберите ПВЗ"
    )
    
    # Поля для каждого часа
    hour_9 = forms.IntegerField(label='09:00-10:00', min_value=0, initial=0)
    hour_10 = forms.IntegerField(label='10:00-11:00', min_value=0, initial=0)
    hour_11 = forms.IntegerField(label='11:00-12:00', min_value=0, initial=0)
    hour_12 = forms.IntegerField(label='12:00-13:00', min_value=0, initial=0)
    hour_13 = forms.IntegerField(label='13:00-14:00', min_value=0, initial=0)
    hour_14 = forms.IntegerField(label='14:00-15:00', min_value=0, initial=0)
    hour_15 = forms.IntegerField(label='15:00-16:00', min_value=0, initial=0)
    hour_16 = forms.IntegerField(label='16:00-17:00', min_value=0, initial=0)
    hour_17 = forms.IntegerField(label='17:00-18:00', min_value=0, initial=0)
    hour_18 = forms.IntegerField(label='18:00-19:00', min_value=0, initial=0)
    hour_19 = forms.IntegerField(label='19:00-20:00', min_value=0, initial=0)
    hour_20 = forms.IntegerField(label='20:00-21:00', min_value=0, initial=0)
    
    def get_hourly_distribution(self):
        """Получить распределение по часам из формы"""
        if not self.is_valid():
            return None
            
        distribution = {}
        for hour in range(9, 21):  # 9 до 20
            field_name = f'hour_{hour}'
            if field_name in self.cleaned_data:
                distribution[hour] = self.cleaned_data[field_name]
        return distribution
    
    def clean(self):
        cleaned_data = super().clean()
        total_orders = sum(cleaned_data.get(f'hour_{hour}', 0) for hour in range(9, 21))
        
        if total_orders == 0:
            raise forms.ValidationError("Хотя бы для одного часа должно быть указано количество заказов")
        
        if total_orders > 1000:
            raise forms.ValidationError("Слишком большое количество заказов. Максимум 1000 в день.")
        
        return cleaned_data

class OrderGenerationForm(forms.Form):
    pvz = forms.ModelChoiceField(
        label='Пункт выдачи',
        queryset=PVZ.objects.all(),
        empty_label="Выберите ПВЗ",
        required=True
    )
    
    date_range_start = forms.DateField(
        label='Начало периода',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )
    
    date_range_end = forms.DateField(
        label='Конец периода',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('date_range_start')
        end_date = cleaned_data.get('date_range_end')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("Дата начала не может быть позже даты окончания")
            
            # Ограничиваем период генерации (например, 3 месяца)
            max_days = 90
            if (end_date - start_date).days > max_days:
                raise forms.ValidationError(f"Период не может превышать {max_days} дней")
        
        return cleaned_data


class TaskForm(forms.ModelForm):
    """Форма для создания и редактирования задач"""
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'pvz', 'assigned_to', 'deadline', 'priority', 'is_global']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название задачи'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание задачи'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'pvz': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and user.role == 'manager':
            # Менеджер может назначать задачи только на свои ПВЗ
            self.fields['pvz'].queryset = user.pvz.all()
            self.fields['assigned_to'].queryset = User.objects.filter(
                role='employee', 
                pvz__in=user.pvz.all()
            ).distinct()
        elif user and user.role == 'admin':
            # Админ может всё
            self.fields['pvz'].queryset = PVZ.objects.all()
            self.fields['assigned_to'].queryset = User.objects.filter(role='employee')