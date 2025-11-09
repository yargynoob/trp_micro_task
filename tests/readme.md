# Тесты API

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск тестов

Убедитесь, что все сервисы запущены:

```bash
cd ..
docker-compose up -d
```

Подождите несколько секунд, пока сервисы полностью запустятся, затем запустите тесты:

```bash
python test_api.py
```

## Описание тестов

### Базовые проверки
- **Health Check** - проверка доступности API Gateway
- **Unauthorized Access Protection** - защита от неавторизованного доступа
- **Invalid Credentials Handling** - обработка неверных учетных данных
- **Validation** - валидация входных данных

### Аутентификация
- **User Registration** - регистрация нового пользователя
- **User Login** - вход пользователя и получение JWT токена

### Операции с пользователями
- **Get Profile** - получение профиля текущего пользователя

### Операции с заказами
- **Create Order** - создание нового заказа
- **Get Order** - получение заказа по ID
- **Get Orders List** - получение списка заказов с пагинацией
- **Update Order Status** - обновление статуса заказа
- **Get My Stats** - получение статистики пользователя

### Rate Limiting
- **Rate Limiting** - проверка ограничения запросов

## Ожидаемый результат

Все тесты должны пройти успешно:

```
============================================================
Запуск интеграционных тестов API
============================================================

Базовые проверки:
✓ PASS Health Check
✓ PASS Unauthorized Access Protection
✓ PASS Invalid Credentials Handling
✓ PASS Validation (Short Password)

Аутентификация:
✓ PASS User Registration
✓ PASS User Login

Операции с пользователями:
✓ PASS Get Profile

Операции с заказами:
✓ PASS Create Order
✓ PASS Get Order
✓ PASS Get Orders List
✓ PASS Update Order Status
✓ PASS Get My Stats

Rate Limiting:
✓ PASS Rate Limiting

============================================================
Все тесты пройдены! 14/14
============================================================
```
