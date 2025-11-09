"""
Модуль для Rate Limiting в API Gateway
"""
from datetime import datetime, timedelta
from collections import defaultdict
import threading
from functools import wraps
from flask import request, jsonify
from logger import logger

class RateLimiter:
    """
    Rate Limiter для ограничения количества запросов
    Использует алгоритм Sliding Window
    """
    
    def __init__(self, max_requests=100, window_seconds=60):
        """
        :param max_requests: Максимум запросов в окне
        :param window_seconds: Размер окна в секундах
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # IP -> список timestamp'ов
        self.lock = threading.Lock()
    
    def is_allowed(self, identifier):
        """
        Проверяет, разрешен ли запрос для данного идентификатора
        
        :param identifier: Идентификатор (IP адрес, user_id и т.д.)
        :return: (allowed: bool, remaining: int, reset_time: datetime)
        """
        with self.lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            # Получаем запросы для данного идентификатора
            user_requests = self.requests[identifier]
            
            # Удаляем старые запросы за пределами окна
            user_requests[:] = [req_time for req_time in user_requests if req_time > window_start]
            
            # Проверяем лимит
            if len(user_requests) >= self.max_requests:
                # Вычисляем время сброса (когда истечет самый старый запрос)
                reset_time = user_requests[0] + timedelta(seconds=self.window_seconds)
                remaining = 0
                allowed = False
            else:
                # Добавляем текущий запрос
                user_requests.append(now)
                self.requests[identifier] = user_requests
                remaining = self.max_requests - len(user_requests)
                reset_time = now + timedelta(seconds=self.window_seconds)
                allowed = True
            
            return allowed, remaining, reset_time
    
    def get_identifier(self):
        """
        Получает идентификатор для rate limiting
        Приоритет: user_id из токена > IP адрес
        """
        # Если есть аутентифицированный пользователь, используем его ID
        if hasattr(request, 'user') and request.user:
            return f"user:{request.user.get('user_id')}"
        
        # Иначе используем IP адрес
        return f"ip:{request.remote_addr}"
    
    def cleanup_old_entries(self):
        """
        Очистка старых записей (для фоновой задачи)
        """
        with self.lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds * 2)
            
            # Удаляем записи, которые полностью устарели
            to_delete = []
            for identifier, timestamps in self.requests.items():
                timestamps[:] = [t for t in timestamps if t > window_start]
                if not timestamps:
                    to_delete.append(identifier)
            
            for identifier in to_delete:
                del self.requests[identifier]

# Глобальные rate limiters с разными лимитами
# Общий лимит для всех запросов
global_limiter = RateLimiter(max_requests=100, window_seconds=60)

# Строгий лимит для операций входа/регистрации
auth_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Лимит для создания заказов
order_creation_limiter = RateLimiter(max_requests=20, window_seconds=60)


def rate_limit(limiter=None):
    """
    Декоратор для применения rate limiting к маршрутам
    
    :param limiter: RateLimiter для использования (по умолчанию global_limiter)
    """
    if limiter is None:
        limiter = global_limiter
    
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            identifier = limiter.get_identifier()
            allowed, remaining, reset_time = limiter.is_allowed(identifier)
            
            if not allowed:
                logger.warning(
                    'Rate limit exceeded',
                    identifier=identifier,
                    endpoint=request.endpoint,
                    path=request.path
                )
                
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Too many requests. Please try again later.',
                        'retry_after': int((reset_time - datetime.now()).total_seconds())
                    }
                }), 429
            
            # Добавляем заголовки rate limit
            response = f(*args, **kwargs)
            
            # Если response - это tuple (response, status_code)
            if isinstance(response, tuple):
                resp_obj, status_code = response
                if hasattr(resp_obj, 'headers'):
                    resp_obj.headers['X-RateLimit-Limit'] = str(limiter.max_requests)
                    resp_obj.headers['X-RateLimit-Remaining'] = str(remaining)
                    resp_obj.headers['X-RateLimit-Reset'] = reset_time.isoformat()
                return resp_obj, status_code
            else:
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Limit'] = str(limiter.max_requests)
                    response.headers['X-RateLimit-Remaining'] = str(remaining)
                    response.headers['X-RateLimit-Reset'] = reset_time.isoformat()
                return response
        
        return wrapped
    
    return decorator
