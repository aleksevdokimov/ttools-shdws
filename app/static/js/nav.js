// Навигация - общие функции для всех страниц

// Обновление навигации с сервером
function updateNavServer(serverName, playerName) {
    const serverContainer = document.getElementById('nav-server-container');
    const serverLink = document.getElementById('nav-server-link');
    const playerSpan = document.getElementById('nav-player');
    
    // Отображение игрока (слева от сервера)
    if (playerSpan) {
        if (playerName) {
            playerSpan.textContent = playerName;
            playerSpan.title = 'Игрок';
        } else {
            playerSpan.textContent = 'Не выбран';
            playerSpan.title = 'Игрок не связан с аккаунтом';
        }
        playerSpan.style.display = 'inline';
    }
    
    // Отображение сервера (справа от игрока)
    if (serverContainer && serverLink) {
        if (serverName) {
            serverLink.textContent = serverName;
            serverLink.href = '/my-servers/';
            serverLink.title = 'Сменить сервер';
        } else {
            serverLink.textContent = 'Не выбран';
            serverLink.href = '/my-servers/';
            serverLink.title = 'Выбрать сервер';
        }
        serverContainer.style.display = 'flex';
    }
}

// Обновление ссылок на альянсы, игроков, деревни и поиск клеток
function updateGameLinks(serverId) {
    const alliancesLink = document.getElementById('game-alliances-link');
    const playersLink = document.getElementById('game-players-link');
    const villagesLink = document.getElementById('game-villages-link');
    const mapSearchLink = document.getElementById('game-map-search-link');

    if (serverId) {
        if (alliancesLink) {
            alliancesLink.href = `/game/servers/${serverId}/alliances`;
            alliancesLink.style.display = 'flex';
        }
        if (playersLink) {
            playersLink.href = `/game/servers/${serverId}/players`;
            playersLink.style.display = 'flex';
        }
        if (villagesLink) {
            villagesLink.href = `/game/servers/${serverId}/villages`;
            villagesLink.style.display = 'flex';
        }
        if (mapSearchLink) {
            mapSearchLink.href = `/game/servers/${serverId}/map-search`;
            mapSearchLink.style.display = 'flex';
        }

        // Показать блок "Выбранный сервер"
        const selectedServerSection = document.getElementById('selected-server-section');
        const selectedServerTitle = document.getElementById('selected-server-title');
        if (selectedServerSection) selectedServerSection.style.display = 'block';
        if (selectedServerTitle) selectedServerTitle.style.display = 'block';
    } else {
        if (alliancesLink) alliancesLink.style.display = 'none';
        if (playersLink) playersLink.style.display = 'none';
        if (villagesLink) villagesLink.style.display = 'none';
        if (mapSearchLink) mapSearchLink.style.display = 'none';

        // Скрыть блок "Выбранный сервер"
        const selectedServerSection = document.getElementById('selected-server-section');
        const selectedServerTitle = document.getElementById('selected-server-title');
        if (selectedServerSection) selectedServerSection.style.display = 'none';
        if (selectedServerTitle) selectedServerTitle.style.display = 'none';
    }
}

// Загрузка данных пользователя
async function loadUserData() {
    try {
        const response = await fetch('/auth/me/', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const user = await response.json();
            
            // Обновляем имя пользователя
            const userLogin = document.getElementById('user-login');
            if (userLogin) {
                userLogin.textContent = user.username;
            }
            
            // Обновляем отображение сервера в nav
            if (user.selected_server_name) {
                updateNavServer(user.selected_server_name, user.player_name);
            } else {
                updateNavServer(null, null);
            }
            
            // Обновляем ссылки на альянсы, игроков и деревни
            if (user.selected_server_id) {
                updateGameLinks(user.selected_server_id);
            }
            
            // Показываем ссылку "Мои серверы" для всех авторизованных пользователей
            if (document.getElementById('my-servers-link')) {
                document.getElementById('my-servers-link').style.display = 'flex';
            }
            
            // Показываем ссылку "Серверы" для модератора и выше (role_id >= 3)
            if (user.role_id === 4 || user.role_id === 2) {
                if (document.getElementById('servers-link')) {
                    document.getElementById('servers-link').style.display = 'flex';
                }
            }

            // Показываем ссылку "Пользователи" для админа и выше (role_id >= 4)
            if (user.role_id = 4) {
                if (document.getElementById('users-link')) {
                    document.getElementById('users-link').style.display = 'flex';
                }
            }
            
            return user;
        } else {
            window.location.href = '/login';
            return null;
        }
    } catch (error) {
        console.error('Ошибка загрузки данных пользователя:', error);
        return null;
    }
}

// Обработка выхода
function setupLogout() {
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', async (e) => {
            e.preventDefault();
            
            try {
                const response = await fetch('/auth/logout', {
                    method: 'POST',
                    credentials: 'include'
                });
                
                if (response.ok) {
                    window.location.href = '/login';
                }
            } catch (error) {
                console.error('Ошибка выхода:', error);
            }
        });
    }
}

// Инициализация навигации - вызывается из шаблонов страниц
function initNav() {
    setupLogout();
    loadUserData();
}
