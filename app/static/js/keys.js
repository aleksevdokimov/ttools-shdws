let currentPage = 1;
let currentFilters = { token: undefined, used: undefined };

// Загрузка списка ключей
async function loadKeys() {
    try {
        const params = new URLSearchParams({
            page: currentPage,
            per_page: 20
        });

        if (currentFilters.token !== undefined) {
            params.set('token', currentFilters.token);
        }
        if (currentFilters.used !== undefined) {
            params.set('used', currentFilters.used);
        }

        const response = await fetch(`/auth/keys?${params}`, {
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            renderKeys(data.tokens);
            renderPagination(data);
        } else {
            document.getElementById('keys-table-body').innerHTML =
                '<tr><td colspan="8">Ошибка загрузки данных</td></tr>';
        }
    } catch (error) {
        console.error('Ошибка загрузки ключей:', error);
        document.getElementById('keys-table-body').innerHTML =
            '<tr><td colspan="8">Ошибка загрузки данных</td></tr>';
    }
}

// Отрисовка списка ключей
function renderKeys(keys) {
    const tbody = document.getElementById('keys-table-body');

    if (!keys || keys.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8">Ключи не найдены</td></tr>';
        return;
    }

    tbody.innerHTML = keys.map(key => `
            <tr>
                <td>${key.id}</td>
                <td>${escapeHtml(key.token)}</td>
                <td>${key.used_by_user_id || '-'}</td>
                <td>${key.used_at ? 'Да' : 'Нет'}</td>
                <td>${key.expires_at ? formatDate(key.expires_at) : '-'}</td>
                <td>${escapeHtml(key.comment || '-')}</td>
                <td>${formatDate(key.created_at)}</td>
                <td>
                    <button class="btn-secondary" onclick="editComment(${key.id}, '${escapeHtml(key.comment || '')}')">
                        Редактировать
                    </button>
                </td>
            </tr>
        `).join('');
}

// Отрисовка пагинации
function renderPagination(data) {
    const pagination = document.getElementById('pagination');
    const { page, pages } = data;

    if (pages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';

    if (page > 1) {
        html += `<a href="#" class="pagination-link" data-page="${page - 1}">← Назад</a>`;
    }

    for (let i = Math.max(1, page - 2); i <= Math.min(pages, page + 2); i++) {
        html += `<a href="#" class="pagination-link ${i === page ? 'active' : ''}" data-page="${i}">${i}</a>`;
    }

    if (page < pages) {
        html += `<a href="#" class="pagination-link" data-page="${page + 1}">Вперёд →</a>`;
    }

    pagination.innerHTML = html;

    pagination.querySelectorAll('.pagination-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            currentPage = parseInt(link.dataset.page);
            loadKeys();
        });
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('ru-RU');
}

// Генерация ключей
document.getElementById('generate-keys-btn').addEventListener('click', async () => {
    const countInput = document.getElementById('keys-count');
    const count = parseInt(countInput.value);

    if (isNaN(count) || count < 1 || count > 30) {
        showToast('Количество ключей должно быть от 1 до 30', 'error');
        return;
    }

    try {
        const response = await fetch('/auth/keys/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ count }),
            credentials: 'include'
        });

        if (response.ok) {
            showToast('Ключи сгенерированы', 'success');
            loadKeys();
        } else {
            const data = await response.json();
            showToast(data.detail || 'Ошибка генерации ключей', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showToast('Ошибка генерации ключей', 'error');
    }
});

// Применение фильтров
document.getElementById('apply-filters').addEventListener('click', () => {
    const usedValue = document.getElementById('filter-used').value;
    currentFilters = {
        token: document.getElementById('filter-token').value,
        used: usedValue === "" ? undefined : (usedValue === "true")
    };
    currentPage = 1;
    loadKeys();
});

// Очистка фильтров
document.getElementById('clear-filters').addEventListener('click', () => {
    document.getElementById('filter-token').value = '';
    document.getElementById('filter-used').value = '';
    currentFilters = { token: undefined, used: undefined };
    currentPage = 1;
    loadKeys();
});

// Редактирование комментария
function editComment(keyId, currentComment) {
    document.getElementById('edit-key-id').value = keyId;
    document.getElementById('edit-comment').value = currentComment;
    document.getElementById('edit-comment-modal').style.display = 'flex';
}

// Закрытие модального окна
document.querySelector('#edit-comment-modal .close').addEventListener('click', () => {
    document.getElementById('edit-comment-modal').style.display = 'none';
});

// Сохранение комментария
document.getElementById('edit-comment-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const keyId = document.getElementById('edit-key-id').value;
    const comment = document.getElementById('edit-comment').value;

    try {
        const response = await fetch(`/auth/keys/${keyId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ comment }),
            credentials: 'include'
        });

        if (response.ok) {
            showToast('Комментарий сохранён', 'success');
            document.getElementById('edit-comment-modal').style.display = 'none';
            loadKeys();
        } else {
            const data = await response.json();
            showToast(data.detail || 'Ошибка сохранения комментария', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showToast('Ошибка сохранения комментария', 'error');
    }
});

// Закрытие по клику вне модального окна
document.getElementById('edit-comment-modal').addEventListener('click', (e) => {
    if (e.target.id === 'edit-comment-modal') {
        e.target.style.display = 'none';
    }
});

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    loadKeys();
});