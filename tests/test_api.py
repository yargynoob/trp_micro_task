"""
Интеграционные тесты для API
"""
import requests
import time
import uuid

BASE_URL = "http://localhost:8080"

# Цвета для вывода
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
YELLOW = "\033[93m"

def print_test(name, passed, message=""):
    """Красивый вывод результата теста"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} {name}")
    if message and not passed:
        print(f"     {message}")

def test_health_check():
    """Тест проверки здоровья системы"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        passed = response.status_code == 200 and response.json().get('status') == 'OK'
        print_test("Health Check", passed)
        return passed
    except Exception as e:
        print_test("Health Check", False, str(e))
        return False

def test_user_registration():
    """Тест регистрации пользователя"""
    try:
        email = f"test_{uuid.uuid4()}@example.com"
        data = {
            "email": email,
            "password": "password123",
            "name": "Test User"
        }
        response = requests.post(f"{BASE_URL}/v1/users/register", json=data, timeout=5)
        passed = response.status_code == 201
        print_test("User Registration", passed)
        return passed, email if passed else None
    except Exception as e:
        print_test("User Registration", False, str(e))
        return False, None

def test_user_login(email):
    """Тест входа пользователя"""
    try:
        data = {
            "email": email,
            "password": "password123"
        }
        response = requests.post(f"{BASE_URL}/v1/users/login", json=data, timeout=5)
        passed = response.status_code == 200 and 'token' in response.json().get('data', {})
        token = response.json()['data']['token'] if passed else None
        print_test("User Login", passed)
        return passed, token
    except Exception as e:
        print_test("User Login", False, str(e))
        return False, None

def test_get_profile(token):
    """Тест получения профиля"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/v1/users/profile", headers=headers, timeout=5)
        passed = response.status_code == 200
        print_test("Get Profile", passed)
        return passed
    except Exception as e:
        print_test("Get Profile", False, str(e))
        return False

def test_create_order(token):
    """Тест создания заказа"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "items": [
                {"product": "Test Product 1", "quantity": 2, "price": 99.99},
                {"product": "Test Product 2", "quantity": 1, "price": 49.99}
            ]
        }
        response = requests.post(f"{BASE_URL}/v1/orders", json=data, headers=headers, timeout=5)
        passed = response.status_code == 201
        order_id = response.json().get('data', {}).get('id') if passed else None
        print_test("Create Order", passed)
        return passed, order_id
    except Exception as e:
        print_test("Create Order", False, str(e))
        return False, None

def test_get_order(token, order_id):
    """Тест получения заказа"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/v1/orders/{order_id}", headers=headers, timeout=5)
        passed = response.status_code == 200
        print_test("Get Order", passed)
        return passed
    except Exception as e:
        print_test("Get Order", False, str(e))
        return False

def test_get_orders(token):
    """Тест получения списка заказов"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/v1/orders?page=1&per_page=10", headers=headers, timeout=5)
        passed = response.status_code == 200
        print_test("Get Orders List", passed)
        return passed
    except Exception as e:
        print_test("Get Orders List", False, str(e))
        return False

def test_update_order_status(token, order_id):
    """Тест обновления статуса заказа"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {"status": "cancelled"}
        response = requests.put(f"{BASE_URL}/v1/orders/{order_id}/status", json=data, headers=headers, timeout=5)
        passed = response.status_code == 200
        print_test("Update Order Status", passed)
        return passed
    except Exception as e:
        print_test("Update Order Status", False, str(e))
        return False

def test_my_stats(token):
    """Тест получения своей статистики"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/v1/orders/my-stats", headers=headers, timeout=5)
        passed = response.status_code == 200
        print_test("Get My Stats", passed)
        return passed
    except Exception as e:
        print_test("Get My Stats", False, str(e))
        return False

def test_rate_limiting():
    """Тест rate limiting"""
    try:
        # Делаем много запросов подряд
        email = f"ratelimit_{uuid.uuid4()}@example.com"
        success_count = 0
        rate_limited = False
        
        for i in range(15):  # Auth limiter: 10 запросов в минуту
            data = {
                "email": email,
                "password": "password123",
                "name": "Rate Test"
            }
            response = requests.post(f"{BASE_URL}/v1/users/register", json=data, timeout=5)
            if response.status_code == 429:
                rate_limited = True
                break
            elif response.status_code < 500:
                success_count += 1
            time.sleep(0.1)
        
        passed = rate_limited  # Должны получить 429 после лимита
        print_test("Rate Limiting", passed, f"Successful: {success_count}, Limited: {rate_limited}")
        return passed
    except Exception as e:
        print_test("Rate Limiting", False, str(e))
        return False

def test_unauthorized_access():
    """Тест доступа без токена"""
    try:
        response = requests.get(f"{BASE_URL}/v1/users/profile", timeout=5)
        passed = response.status_code == 401
        print_test("Unauthorized Access Protection", passed)
        return passed
    except Exception as e:
        print_test("Unauthorized Access Protection", False, str(e))
        return False

def test_invalid_credentials():
    """Тест входа с неверными данными"""
    try:
        data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        response = requests.post(f"{BASE_URL}/v1/users/login", json=data, timeout=5)
        passed = response.status_code == 401
        print_test("Invalid Credentials Handling", passed)
        return passed
    except Exception as e:
        print_test("Invalid Credentials Handling", False, str(e))
        return False

def test_validation():
    """Тест валидации данных"""
    try:
        # Пароль слишком короткий
        data = {
            "email": "test@example.com",
            "password": "123",  # Меньше 6 символов
            "name": "Test"
        }
        response = requests.post(f"{BASE_URL}/v1/users/register", json=data, timeout=5)
        passed = response.status_code == 400
        print_test("Validation (Short Password)", passed)
        return passed
    except Exception as e:
        print_test("Validation (Short Password)", False, str(e))
        return False

def run_all_tests():
    """Запуск всех тестов"""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}Запуск интеграционных тестов API{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}\n")
    
    results = []
    
    # Базовые тесты
    print(f"{YELLOW}Базовые проверки:{RESET}")
    results.append(test_health_check())
    results.append(test_unauthorized_access())
    results.append(test_invalid_credentials())
    results.append(test_validation())
    
    # Тесты с аутентификацией
    print(f"\n{YELLOW}Аутентификация:{RESET}")
    passed, email = test_user_registration()
    results.append(passed)
    
    if passed and email:
        passed, token = test_user_login(email)
        results.append(passed)
        
        if passed and token:
            # Тесты пользователей
            print(f"\n{YELLOW}Операции с пользователями:{RESET}")
            results.append(test_get_profile(token))
            
            # Тесты заказов
            print(f"\n{YELLOW}Операции с заказами:{RESET}")
            passed, order_id = test_create_order(token)
            results.append(passed)
            
            if passed and order_id:
                results.append(test_get_order(token, order_id))
                results.append(test_get_orders(token))
                results.append(test_update_order_status(token, order_id))
                results.append(test_my_stats(token))
    
    # Rate Limiting
    print(f"\n{YELLOW}Rate Limiting:{RESET}")
    results.append(test_rate_limiting())
    
    # Итоги
    passed_count = sum(results)
    total_count = len(results)
    
    print(f"\n{YELLOW}{'='*60}{RESET}")
    if passed_count == total_count:
        print(f"{GREEN}Все тесты пройдены! {passed_count}/{total_count}{RESET}")
    else:
        print(f"{RED}Провалено тестов: {total_count - passed_count}/{total_count}{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}\n")
    
    return passed_count == total_count

if __name__ == "__main__":
    run_all_tests()
