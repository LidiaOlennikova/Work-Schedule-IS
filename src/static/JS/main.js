// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    initializeSidebar();
    initializeCalendarToggle();
    initializeUserMenu();
    initializeCompactNotifications();
    updateTime();
});

// ===== SIDEBAR TOGGLE =====
function initializeSidebar() {
    const menuToggle = document.querySelector('.menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            const sidebar = document.querySelector('.sidebar');
            const mainContent = document.querySelector('.main-content');
            
            if (sidebar && mainContent) {
                sidebar.classList.toggle('active');
                mainContent.classList.toggle('active');
            }
        });
    }
}

// ===== CALENDAR TOGGLE =====
function initializeCalendarToggle() {
    const toggleBtn = document.querySelector('.toggle-btn');
    const calendarTime = document.querySelector('.calendar-time');
    
    if (toggleBtn && calendarTime) {
        toggleBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            calendarTime.classList.add('collapsed');
        });
        
        calendarTime.addEventListener('click', function(e) {
            if (this.classList.contains('collapsed')) {
                this.classList.remove('collapsed');
            }
        });
    }
}

// ===== USER MENU TOGGLE =====
function initializeUserMenu() {
    const userMenu = document.getElementById('userMenu');
    const userAvatar = document.querySelector('.user-avatar');
    
    if (userMenu && userAvatar) {
        userAvatar.addEventListener('click', function(e) {
            e.stopPropagation();
            userMenu.classList.toggle('collapsed');
        });
        
        // Close user menu when clicking outside
        document.addEventListener('click', function(e) {
            if (userMenu && !userMenu.contains(e.target)) {
                userMenu.classList.add('collapsed');
            }
        });
    }
}

// ===== COMPACT NOTIFICATIONS =====
function initializeCompactNotifications() {
    const notification = document.querySelector('.notification-compact');
    if (notification) {
        notification.addEventListener('click', function(e) {
            e.stopPropagation();
            const dropdown = document.querySelector('.notification-dropdown-compact');
            if (dropdown) {
                dropdown.classList.toggle('active');
                // Загружаем уведомления при открытии
                if (dropdown.classList.contains('active')) {
                    loadNotifications();
                }
            }
        });
        
        // Close notification dropdown when clicking outside
        document.addEventListener('click', function(e) {
            const dropdown = document.querySelector('.notification-dropdown-compact');
            if (dropdown && !notification.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('active');
            }
        });
    }
}

// ===== NOTIFICATIONS FUNCTIONS =====
function loadNotifications() {
    fetch('/get-notifications/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateNotificationBadge(data.unread_count);
            renderNotifications(data.notifications);
        }
    })
    .catch(error => {
        console.error('Error loading notifications:', error);
    });
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (badge) {
        badge.textContent = count;
        if (count === 0) {
            badge.style.display = 'none';
        } else {
            badge.style.display = 'flex';
            // Анимация для новых уведомлений
            badge.classList.add('new');
            setTimeout(() => badge.classList.remove('new'), 500);
        }
    }
}

function renderNotifications(notifications) {
    const notificationList = document.getElementById('notificationList');
    if (!notificationList) return;

    if (notifications.length === 0) {
        notificationList.innerHTML = '<div class="no-notifications">Нет уведомлений</div>';
        return;
    }

    let html = '';
    notifications.forEach(notification => {
        html += `
            <div class="notification-item-compact ${notification.is_read ? 'read' : 'unread'}" data-id="${notification.id}">
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${notification.created_at}</div>
                </div>
                ${!notification.is_read ? '<button class="mark-read-btn" onclick="markNotificationRead(this, ' + notification.id + ')">✓</button>' : ''}
            </div>
        `;
    });

    notificationList.innerHTML = html;
}

function markNotificationRead(button, notificationId) {
    fetch('/mark-notification-read/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            notification_id: notificationId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const notificationItem = button.closest('.notification-item-compact');
            notificationItem.classList.remove('unread');
            notificationItem.classList.add('read');
            button.remove();
            updateNotificationBadge(data.unread_count);
        }
    })
    .catch(error => {
        console.error('Error marking notification read:', error);
    });
}

// Mark all as read
document.addEventListener('DOMContentLoaded', function() {
    const markAllReadBtn = document.getElementById('markAllRead');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function() {
            fetch('/mark-notification-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    notification_id: 'all'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.querySelectorAll('.notification-item-compact').forEach(item => {
                        item.classList.remove('unread');
                        item.classList.add('read');
                    });
                    document.querySelectorAll('.mark-read-btn').forEach(btn => btn.remove());
                    updateNotificationBadge(data.unread_count);
                }
            })
            .catch(error => {
                console.error('Error marking all notifications read:', error);
            });
        });
    }

    // Load notifications on page load
    loadNotifications();

    // Refresh notifications every 30 seconds
    setInterval(loadNotifications, 30000);
});

// ===== TIME UPDATER =====
function updateTime() {
    const now = new Date();
    const timeElement = document.querySelector('.time');
    const dateElement = document.querySelector('.date');
    
    if (timeElement && dateElement) {
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const dateString = now.toLocaleDateString('ru-RU', options);
        
        timeElement.textContent = `${hours}:${minutes}`;
        dateElement.textContent = dateString;
    }
}

// Update time every halfminute
setInterval(updateTime, 30000);

// ===== CSRF TOKEN =====
function getCsrfToken() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfToken ? csrfToken.value : '';
}



// ===== TASKS FUNCTIONS =====

function loadTasks(filters = {}) {
    const url = new URL('/api/tasks/', window.location.origin);
    if (filters.status) url.searchParams.append('status', filters.status);
    if (filters.pvz_id) url.searchParams.append('pvz_id', filters.pvz_id);
    
    return fetch(url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Error loading tasks:', error);
        return { success: false, tasks: [] };
    });
}

function createTask(taskData) {
    return fetch('/api/tasks/create/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json());
}

function completeTask(taskId) {
    return fetch(`/api/tasks/${taskId}/complete/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({})
    })
    .then(response => response.json());
}

function deleteTask(taskId) {
    return fetch(`/api/tasks/${taskId}/delete/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json());
}

function updateTask(taskId, taskData) {
    return fetch(`/api/tasks/${taskId}/update/`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json());
}

function changeTaskStatus(taskId, status) {
    return fetch(`/api/tasks/${taskId}/status/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ status: status })
    })
    .then(response => response.json());
}