# Микросервисная архитектура для управления задачами

Техническое задание для разработки микросервисной структуры управления задачами строительных объектов.

## Описание проекта

Проект представляет собой микросервисную архитектуру на Python с тремя основными компонентами:
- **API Gateway** - единая точка входа для клиентских запросов
- **Service Users** - сервис управления пользователями
- **Service Orders** - сервис управления заказами

Система предназначена для:
- Инженеров (регистрация дефектов, обновление информации)
- Менеджеров (назначение задач, контроль сроков, формирование отчётов)
- Руководителей и заказчиков (просмотр прогресса и отчётности)

## Технологический стек

- **Backend**: Python 3.12, Flask
- **База данных**: PostgreSQL 17
- **ORM**: SQLAlchemy 2.0
- **Миграции**: Alembic
- **Валидация**: Pydantic
- **Контейнеризация**: Docker
- **Архитектура**: Микросервисы с API Gateway, Circuit Breaker

## Требования

- Docker Desktop (с поддержкой WSL2 для Windows)
- Git

## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd trp_micro_task
```

### 2. Запуск всех сервисов

```bash
docker-compose up --build
```

Сервисы будут доступны по адресам:
- API Gateway: http://localhost:8000
- PostgreSQL: localhost:5432

### 3. Проверка работы

```bash
# Проверка API Gateway
curl http://localhost:8000/health

# Проверка сервиса пользователей через Gateway
curl http://localhost:8000/users

# Проверка сервиса заказов через Gateway
curl http://localhost:8000/orders
```

## Структура проекта

```
trp_micro_task/
├── api_gateway/           # API Gateway сервис
│   ├── app.py            # Основной файл приложения
│   ├── Dockerfile
│   └── requirements.txt
├── service_users/         # Сервис пользователей
│   ├── app.py            # Основной файл приложения
│   ├── models.py         # Модели базы данных
│   ├── database.py       # Настройка подключения к БД
│   ├── schemas.py        # Pydantic схемы валидации
│   ├── init_db.py        # Скрипт инициализации БД
│   ├── alembic/          # Миграции Alembic
│   ├── Dockerfile
│   └── requirements.txt
├── service_orders/        # Сервис заказов
│   ├── app.py            # Основной файл приложения
│   ├── models.py         # Модели базы данных
│   ├── database.py       # Настройка подключения к БД
│   ├── schemas.py        # Pydantic схемы валидации
│   ├── init_db.py        # Скрипт инициализации БД
│   ├── alembic/          # Миграции Alembic
│   ├── Dockerfile
│   └── requirements.txt
└── docker-compose.yml     # Оркестрация сервисов
```

## Модели данных

### Пользователь (User)
- `id` - UUID (первичный ключ)
- `email` - String (уникальный)
- `password_hash` - String
- `name` - String
- `roles` - Array[String] (default: ['user'])
- `created_at` - DateTime
- `updated_at` - DateTime

### Заказ (Order)
- `id` - UUID (первичный ключ)
- `user_id` - UUID (внешний ключ)
- `items` - JSON (состав позиций: товар-количество)
- `status` - String (created, in_progress, completed, cancelled)
- `total_amount` - Decimal(10, 2)
- `created_at` - DateTime
- `updated_at` - DateTime

## API Endpoints

### API Gateway (порт 8000)

#### Пользователи
- `GET /users` - Получить список всех пользователей
- `POST /users` - Создать нового пользователя
- `GET /users/{id}` - Получить пользователя по ID
- `PUT /users/{id}` - Обновить пользователя
- `DELETE /users/{id}` - Удалить пользователя
- `GET /users/{id}/details` - Получить пользователя с его заказами

#### Заказы
- `GET /orders` - Получить список заказов (опционально ?userId=<uuid>)
- `POST /orders` - Создать новый заказ
- `GET /orders/{id}` - Получить заказ по ID
- `PUT /orders/{id}` - Обновить заказ
- `DELETE /orders/{id}` - Удалить заказ

#### Служебные
- `GET /health` - Проверка состояния Gateway и Circuit Breakers
- `GET /status` - Статус Gateway

## Формат ответов

### Успешный ответ
```json
{
  "success": true,
  "data": { ... }
}
```

### Ответ с ошибкой
```json
{
  "success": false,
  "error": {
        "code": "Код ошибки",
    "message": "Описание ошибки"
  }
}
```

## Примеры использования

### Создание пользователя

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "Белов Ярослав"
  }'
```

### Создание заказа

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user_uuid>",
    "items": [
      {
        "product": "Чокопай",
        "quantity": 10,
        "price": 52.00
      }
    ]
  }'
```

### Получение заказов пользователя

```bash
curl http://localhost:8000/users/<user_uuid>/details
```

## Особенности реализации

### Circuit Breaker
API Gateway использует паттерн Circuit Breaker для повышения отказоустойчивости:
- Автоматическое отключение при высоком проценте ошибок
- Периодическая проверка восстановления сервиса
- Защита от каскадных сбоев

### База данных
- PostgreSQL с автоматической инициализацией при первом запуске
- Использование UUID вместо auto-increment ID
- Миграции через Alembic для версионирования схемы

## Разработка

### Логирование
Логи доступны через Docker:
```bash
docker-compose logs -f api_gateway
docker-compose logs -f service_users
docker-compose logs -f service_orders
```

### Остановка сервисов
```bash
docker-compose down
```

### Полная очистка (включая БД)
```bash
docker-compose down -v
```
