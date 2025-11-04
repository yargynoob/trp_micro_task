"""Скрипт для инициализации базы данных"""
import time
from sqlalchemy import text
from database import engine, Base
from models import User

def wait_for_db(max_retries=30):
    """Ожидание готовности базы данных"""
    print("Ожидание подключения к базе данных...")
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("База данных доступна!")
            return True
        except Exception as e:
            print(f"Попытка {i+1}/{max_retries}: База данных недоступна, ожидание... ({e})")
            time.sleep(2)
    raise Exception("Не удалось подключиться к базе данных")

def init_database():
    """Инициализация базы данных"""
    wait_for_db()
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы!")

if __name__ == "__main__":
    init_database()
