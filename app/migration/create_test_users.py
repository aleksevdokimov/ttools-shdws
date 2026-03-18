"""
Скрипт для создания тестовых пользователей.
Создает 4 пользователей с разными ролями:
- Администратор / админ123 / роль Админ (id=4)
- Модер / модер123 / роль Модератор (id=2)
- Али-модер / амодер123 / роль Альянс-модератор (id=3)
- Вано / игрок123 / роль Игрок (id=1)
"""
import sqlite3
import os
from passlib.context import CryptContext

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'db.sqlite3')

# Хеширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_test_users():
    print(f"Подключение к БД: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Создаем тестовых пользователей
        users = [
            ("Администратор", "admin@example.com", hash_password("админ123"), 4),
            ("Модер", "moder@example.com", hash_password("модер123"), 2),
            ("Али-модер", "alimoder@example.com", hash_password("амодер123"), 3),
            ("Вано", "vano@example.com", hash_password("игрок123"), 1),
        ]
        
        print("Создание тестовых пользователей...")
        cursor.executemany(
            "INSERT INTO users (username, email, password, role_id) VALUES (?, ?, ?, ?)",
            users
        )
        
        conn.commit()
        print("Пользователи успешно созданы!")
        
        # Проверим результат
        cursor.execute("""
            SELECT u.id, u.username, u.email, r.name as role_name, r.id as role_id 
            FROM users u 
            JOIN roles r ON u.role_id = r.id
        """)
        users = cursor.fetchall()
        print("\nСозданные пользователи:")
        for user in users:
            print(f"  id={user[0]}, username={user[1]}, email={user[2]}, role={user[3]} (id={user[4]})")
            
    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    create_test_users()
