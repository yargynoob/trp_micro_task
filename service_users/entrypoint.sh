#!/bin/sh

echo "Инициализация базы данных..."
python init_db.py

echo "Запуск приложения..."
python app.py
