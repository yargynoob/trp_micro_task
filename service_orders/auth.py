"""Утилиты для проверки JWT токенов в сервисе заказов"""
import os
import jwt
from functools import wraps
from flask import request, jsonify

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'


def decode_token(token: str) -> dict:
    """Декодирование JWT токена"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')


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
    """Декоратор для защиты эндпоинтов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = get_token_from_header()
            payload = decode_token(token)
            request.user = payload
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


def require_role(*allowed_roles):
    """Декоратор для проверки ролей пользователя"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                token = get_token_from_header()
                payload = decode_token(token)
                user_roles = payload.get('roles', [])
                
                if not any(role in user_roles for role in allowed_roles):
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 'FORBIDDEN',
                            'message': 'Insufficient permissions'
                        }
                    }), 403
                
                request.user = payload
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
    return decorator
