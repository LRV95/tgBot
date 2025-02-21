import sqlite3
import os
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def drop_users_table(db_path='./database.db'):
    """Удаляет таблицу пользователей."""
    try:
        # Проверяем существование файла БД
        if not os.path.exists(db_path):
            logger.warning(f"База данных не найдена по пути: {db_path}")
            return False

        # Подключаемся к БД
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Удаляем таблицу users
        cursor.execute("DROP TABLE IF EXISTS users")
        
        # Применяем изменения
        conn.commit()

        logger.info("Таблица users успешно удалена")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при удалении таблицы users: {e}")
        return False

    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    db_path = script_dir / 'database.db'
    
    if drop_users_table(db_path):
        print("✅ Таблица пользователей успешно удалена")
    else:
        print("❌ Произошла ошибка при удалении таблицы") 