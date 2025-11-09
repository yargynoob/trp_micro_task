# Микросервисная архитектура с API Gateway

Полнофункциональная микросервисная система управления пользователями и заказами с JWT аутентификацией, Rate Limiting, Circuit Breaker и структурированным логированием.

## Описание проекта

Проект представляет собой микросервисную архитектуру на Python с тремя основными компонентами:
- **API Gateway** - единая точка входа с защитой и мониторингом
- **Service Users** - сервис управления пользователями и аутентификацией
- **Service Orders** - сервис управления заказами

### Ключевые возможности

**Безопасность:**
- JWT аутентификация
- Хэширование паролей
- Rate Limiting

**Надежность:**
- Circuit Breaker для каждого сервиса
- Автоматическое восстановление
- Структурированное логирование (JSON)

## Технологический стек

- **Backend**: Python 3.12, Flask 3.0
- **База данных**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Валидация**: Pydantic 2.5
- **Аутентификация**: PyJWT 2.8, bcrypt 4.1
- **Контейнеризация**: Docker

## Требования

- **Docker Desktop** (с поддержкой WSL2 для Windows)
- **Git**

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd trp_micro_task
```

### 2. Запуск всех сервисов

```bash
docker-compose up --build -d
```

### 3. Проверка статуса

```bash
docker-compose ps
```

Сервисы доступны на следующих портах:
- **API Gateway**: http://localhost:8080
- **PostgreSQL**: localhost:5432

### 4. Проверка работы системы

**Windows PowerShell:**
```powershell
Invoke-RestMethod -Uri http://localhost:8080/health
```

**Linux/Mac/Bash:**
```bash
curl http://localhost:8080/health
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

### API Gateway (порт 8080)

Все эндпоинты используют префикс `/v1/`

#### Аутентификация (публичные)
- `POST /v1/users/register` - Регистрация нового пользователя
- `POST /v1/users/login` - Вход (получение JWT токена)

#### Пользователи (требуют JWT)
- `GET /v1/users/profile` - Получить свой профиль
- `PUT /v1/users/profile` - Обновить свой профиль
- `PUT /v1/users/password` - Изменить свой пароль
- `GET /v1/users` - Получить список пользователей (только admin)
- `GET /v1/users/{id}` - Получить пользователя по ID (только admin)
- `PUT /v1/users/{id}/roles` - Обновить роли пользователя (только admin)
- `DELETE /v1/users/{id}` - Удалить пользователя (только admin)
- `GET /v1/users/search?query={text}` - Поиск пользователей (только admin)

#### Заказы (требуют JWT)
- `POST /v1/orders` - Создать новый заказ
- `GET /v1/orders` - Получить список заказов (с фильтрацией и пагинацией)
- `GET /v1/orders/{id}` - Получить заказ по ID
- `PUT /v1/orders/{id}` - Обновить заказ
- `PUT /v1/orders/{id}/status` - Обновить статус заказа
- `DELETE /v1/orders/{id}` - Удалить заказ (только admin)
- `GET /v1/orders/my-stats` - Статистика своих заказов
- `GET /v1/orders/stats` - Общая статистика заказов (только admin)

#### Мониторинг (публичные)
- `GET /health` - Здоровье системы и Circuit Breakers
- `GET /metrics` - Метрики системы (требует JWT)

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

### 1. Регистрация нового пользователя

```bash
curl -X POST http://localhost:8080/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"ivan@example.com","password":"password123","name":"Ivan"}'
```

**Ответ:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid-here",
      "email": "ivan@example.com",
      "name": "Ivan",
      "roles": ["user"]
    }
  }
}
```

### 2. Вход и получение JWT токена

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ivan@example.com","password":"password123"}' \
  | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

echo "token: $TOKEN"
```

**Сохраните токен для дальнейших запросов!**

### 3. Получение своего профиля

```bash
  curl http://localhost:8080/v1/users/profile \
  -H "Authorization: Bearer $TOKEN"
```
### 4. Создание заказа

```bash
curl -X POST http://localhost:8080/v1/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
  "items": [
  {
    "product":"Laptop",
    "quantity":1,
    "price":75000.00
      }
     ]
    }'
```

### 5. Просмотр своих заказов
```bash
curl http://localhost:8080/v1/orders \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Статистика заказов
```bash
curl http://localhost:8080/v1/orders/my-stats \
  -H "Authorization: Bearer $TOKEN"
```

### 7. Обновление статуса заказа

```bash
curl -X PUT http://localhost:8080/v1/{ORDER_ID}/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "cancelled"
  }'
```

**Доступные статусы:**
- `created` - создан
- `processing` - в обработке (только admin)
- `completed` - завершен (только admin)
- `cancelled` - отменен (пользователь может только отменить свой заказ)

## Особенности реализации

### Rate Limiting
Защита от злоупотреблений с использованием алгоритма Sliding Window:

| Операция | Лимит | Окно |
|----------|-------|------|
| Регистрация/Вход | 10 запросов | 60 сек |
| Создание заказов | 20 запросов | 60 сек |
| Остальные API | 100 запросов | 60 сек |

**При превышении лимита (429):**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 45
  }
}
```

### Circuit Breaker
API Gateway использует паттерн Circuit Breaker для повышения отказоустойчивости:
- **3 состояния:** closed (работает), open (заблокирован), half_open (тестирование)
- **Метрики доступны:** через `/health` и `/metrics`

### JWT Аутентификация
- **Срок действия:** 24 часа
- **Передача:** Header `Authorization: Bearer <token>`
- **Payload:** user_id, email, roles, exp, iat

### Структурированное логирование
Все логи в JSON формате с контекстом:
```json
{
  "timestamp": "2025-11-09T12:00:00Z",
  "level": "INFO",
  "logger": "api_gateway",
  "message": "Order created successfully",
  "service": "api_gateway",
  "request_id": "abc-123-456",
  "user_id": "uuid",
  "method": "POST",
  "path": "/v1/orders"
}
```

### База данных
- PostgreSQL с автоматической инициализацией при первом запуске
- Использование UUID вместо auto-increment ID
- Health checks для проверки готовности БД
- Автоматическое создание таблиц через entrypoint.sh

## Разработка

### Просмотр логов

```bash
# Все логи в реальном времени
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f api_gateway
docker-compose logs -f service_users
docker-compose logs -f service_orders
```

### Мониторинг

```bash
# Проверка здоровья системы
curl http://localhost:8080/health

# Статус контейнеров
docker-compose ps
```

### Управление сервисами

```bash
# Остановка сервисов
docker-compose down

# Перезапуск
docker-compose restart

# Перезапуск конкретного сервиса
docker-compose restart api_gateway

# Пересборка и запуск
docker-compose up --build -d

# Полная очистка (включая БД и volumes)
docker-compose down -v
```

## Тестирование

### Интеграционные тесты

```bash
cd tests
pip install -r requirements.txt
python test_api.py
```

**14 автоматических тестов:**
- Health Check
- Регистрация и вход
- Получение профиля
- Создание и управление заказами
- Фильтрация и статистика
- Rate Limiting
- Обработка ошибок