/**
 * Toast-уведомления для TTools Shadows
 * Неблокирующие уведомления справа внизу экрана
 */

(function() {
    'use strict';

    // Создаём контейнер для уведомлений при загрузке
    function createContainer() {
        if (document.getElementById('toast-container')) {
            return;
        }
        
        const container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    /**
     * Показать toast-уведомление
     * @param {string} message - Текст сообщения
     * @param {string} type - Тип: 'success' | 'error' | 'info'
     * @param {number} duration - Длительность в мс (по умолчанию 3000)
     */
    function showToast(message, type, duration) {
        // Создаём контейнер если его нет
        createContainer();

        // Значения по умолчанию
        type = type || 'info';
        duration = duration || 15000;

        // Проверяем тип
        if (!['success', 'error', 'info'].includes(type)) {
            type = 'info';
        }

        // Создаём элемент уведомления
        const toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        
        // Цвета для каждого типа (более светлые)
        const colors = {
            'success': '#7bed9f',
            'error': '#ff8787',
            'info': '#a8d8ff'
        };
        toast.style.backgroundColor = colors[type] || colors.info;
        toast.style.color = '#1a1d23';
        
        // Добавляем иконку в зависимости от типа
        let icon = '';
        if (type === 'success') {
            icon = '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
        } else if (type === 'error') {
            icon = '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
        } else {
            icon = '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
        }

        toast.innerHTML = icon + '<span class="toast-message">' + message + '</span>';

        // Добавляем в контейнер
        const container = document.getElementById('toast-container');
        container.appendChild(toast);

        // Запускаем анимацию появления
        requestAnimationFrame(function() {
            toast.classList.add('show');
        });

        // Автоматическое скрытие
        setTimeout(function() {
            toast.classList.remove('show');
            
            // Удаляем элемент после анимации
            setTimeout(function() {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);
    }

    // Экспортируем глобальную функцию
    window.showToast = showToast;
})();
