# auth_app/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST

User = get_user_model()

def get_user_redirect_url(user):
    """Определяет куда редиректить пользователя после входа"""
    # Теперь роль хранится прямо в User, а не в UserProfile
    if user.role == 'admin':
        return 'users'  # Администратор -> управление пользователями
    elif user.role == 'manager':
        return 'index_manager'  # Менеджер -> главная страница менеджера
    elif user.role == 'employee':
        return 'actual_schedule'  # Сотрудник -> его график
    
    return 'index_manager'  # По умолчанию

def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_user_redirect_url(request.user))
        
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.first_name}!')
                return redirect(get_user_redirect_url(user))
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect(get_user_redirect_url(request.user))
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect(get_user_redirect_url(user))
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'form': form})

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('login')

@login_required 
def profile_view(request):
    if request.method == 'POST':
        if 'password_change' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль успешно изменен!')
                return redirect('profile')
            else:
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
        else:
            # Обновление профиля
            user = request.user
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('email')
            user.phone = request.POST.get('phone', '')
            user.save()
            
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
    
    return render(request, 'profile.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('login')