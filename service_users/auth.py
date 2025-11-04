"""Утилиты для аутентификации и авторизации"""
import os
import jwt
from datetime import datetime, timedelta
from passlib.hash import bcrypt
from functools import wraps
from flask import request, jsonify

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def hash_password(password: str) -> str:
    """Хеширование пароля с использованием bcrypt"""
    return bcrypt.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Проверка пароля"""
    return bcrypt.verify(password, hashed)


def create_access_token(user_id: str, email: str, roles: list) -> str:
    """Создание JWT токена"""
    payload = {
        'user_id': user_id,
        'email': email,
        'roles': roles,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


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
