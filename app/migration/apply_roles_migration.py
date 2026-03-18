"""
Скрипт для применения миграции ролей напрямую в SQLite БД.
Выполняет то же что и alembic миграция, но без зависимости от alembic.
"""
import sqlite3
import os

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'db.sqlite3')

def apply_migration():
    print(f"Подключение к БД: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Удаляем всех пользователей
        print("Удаление пользователей...")
        cursor.execute("DELETE FROM users")
        
        # Удаляем все роли
        print("Удаление ролей...")
        cursor.execute("DELETE FROM roles")
        
        # Вставляем новые роли
        print("Создание новых ролей...")
        roles = [
            (1, 'Игрок'),
            (2, 'Модератор'),
            (3, 'Альянс-модератор'),
            (4, 'Админ')
        ]
        cursor.executemany("INSERT INTO roles (id, name) VALUES (?, ?)", roles)
        
        conn.commit()
        print("Миграция успешно применена!")
        
        # Проверим результат
        cursor.execute("SELECT * FROM roles")
        roles = cursor.fetchall()
        print("\nРоли в базе данных:")
        for role in roles:
            print(f"  id={role[0]}, name={role[1]}")
            
    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration()
