"""Middleware для проверки JWT токенов в API Gateway"""
import os
import jwt
from flask import request, jsonify
from functools import wraps

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

PUBLIC_ROUTES = [
    '/v1/users/register',
    '/v1/users/login',
    '/health',
    '/status'
]


def decode_token(token: str) -> dict:
    """Декодирование JWT токена"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')


def is_public_route(path: str) -> bool:
    """Проверка, является ли маршрут публичным"""
    for public_route in PUBLIC_ROUTES:
        if path.startswith(public_route):
            return True
    return False


def get_token_from_header() -> str:
    """Извлечение токена из заголовка Authorization"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise Exception('Authorization header missing')
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise Exception('Invalid authorization header format')
    
    return parts[1]


def require_auth(f):
    """Декоратор для защиты эндпоинтов API Gateway"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_public_route(request.path):
            return f(*args, **kwargs)
        
        try:
            token = get_token_from_header()
            payload = decode_token(token)
            request.user = payload
            request.internal_token = token
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': str(e)
                }
            }), 401
    return decorated_function


def add_auth_headers(headers=None):
    """Добавление заголовков авторизации для внутренних запросов"""
    if headers is None:
        headers = {}
    
    if hasattr(request, 'internal_token') and request.internal_token:
        headers['Authorization'] = f'Bearer {request.internal_token}'
    
    request_id = request.headers.get('X-Request-ID')
    if request_id:
        headers['X-Request-ID'] = request_id
    
    return headers
