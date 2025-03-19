import sqlite3
import os
import logging
from pathlib import Path
import argparse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def drop_table(table_name, db_path='./database.db'):
    """Удаляет указанную таблицу."""
    try:
        # Проверяем существование файла БД
        if not os.path.exists(db_path):
            logger.warning(f"База данных не найдена по пути: {db_path}")
            return False

        # Подключаемся к БД
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Удаляем указанную таблицу
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Применяем изменения
        conn.commit()

        logger.info(f"Таблица {table_name} успешно удалена")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при удалении таблицы {table_name}: {e}")
        return False

    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Удаление таблиц из базы данных')
    parser.add_argument('table', help='Имя таблицы для удаления')
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    db_path = script_dir / 'database.db'
    
    if drop_table(args.table, db_path):
        print(f"✅ Таблица {args.table} успешно удалена")
    else:
        print("❌ Произошла ошибка при удалении таблицы") 