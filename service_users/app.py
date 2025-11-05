from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import User
from auth import hash_password, verify_password, create_access_token, require_auth, require_role
from schemas import UserRegister, UserLogin, UserUpdate, PasswordChange, UserRoleUpdate, UserSearch
from pydantic import ValidationError
import uuid

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 8001))

@app.before_request
def add_request_id():
    """Добавление X-Request-ID к каждому запросу"""
    request.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

@app.route('/v1/users/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    db = SessionLocal()
    try:
        data = request.json
        
        if not data.get('email') or not data.get('password') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Email, password and name are required'
                }
            }), 400
        
        if len(data['password']) < 6:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Password must be at least 6 characters'
                }
            }), 400
        
        existing_user = db.query(User).filter(User.email == data['email']).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'EMAIL_EXISTS',
                    'message': 'User with this email already exists'
                }
            }), 400
        
        password_hash = hash_password(data['password'])
        new_user = User(
            email=data['email'],
            name=data['name'],
            password_hash=password_hash,
            roles=['user']
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        user_dict = new_user.to_dict()
        return jsonify({
            'success': True,
            'data': {
                'user': user_dict,
                'message': 'User registered successfully'
            }
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()


@app.route('/v1/users/login', methods=['POST'])
def login():
    """Вход пользователя"""
    db = SessionLocal()
    try:
        data = request.json
        
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Email and password are required'
                }
            }), 400
        
        user = db.query(User).filter(User.email == data['email']).first()
        if not user or not verify_password(data['password'], user.password_hash):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Invalid email or password'
                }
            }), 401
        
        token = create_access_token(str(user.id), user.email, user.roles)
        
        return jsonify({
            'success': True,
            'data': {
                'token': token,
                'user': user.to_dict()
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()


@app.route('/v1/users/profile', methods=['GET'])
@require_auth
def get_profile():
    """Получение профиля текущего пользователя"""
    db = SessionLocal()
    try:
        user_id = request.user.get('user_id')
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()


@app.route('/v1/users/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Обновление профиля текущего пользователя"""
    db = SessionLocal()
    try:
        user_id = request.user.get('user_id')
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        updates = request.json
        if 'name' in updates:
            user.name = updates['name']
        if 'email' in updates:
            existing = db.query(User).filter(User.email == updates['email'], User.id != user.id).first()
            if existing:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'EMAIL_EXISTS',
                        'message': 'Email already in use'
                    }
                }), 400
            user.email = updates['email']
        
        db.commit()
        db.refresh(user)
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()


@app.route('/v1/users', methods=['GET'])
@require_role('admin')
def get_users():
    """Получение списка пользователей с пагинацией и поиском"""
    db = SessionLocal()
    try:
        # Параметры пагинации
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)
        
        # Поиск
        query = db.query(User)
        search_query = request.args.get('query', '').strip()
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                (User.name.ilike(search_pattern)) | 
                (User.email.ilike(search_pattern))
            )
        
        # Фильтр по роли
        role = request.args.get('role')
        if role:
            query = query.filter(User.roles.contains([role]))
        
        # Подсчет общего количества
        total = query.count()
        
        # Пагинация
        offset = (page - 1) * per_page
        users = query.offset(offset).limit(per_page).all()
        
        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in users],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()


@app.route('/users/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'service': 'Users Service',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

@app.route('/users/status', methods=['GET'])
def status():
    """Status endpoint"""
    return jsonify({'status': 'Users service is running'}), 200

@app.route('/v1/users/<user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """Получение пользователя по ID"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404
        return jsonify({'success': True, 'data': user.to_dict()}), 200
    except ValueError:
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid user ID format'}}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/v1/users/<user_id>', methods=['PUT'])
@require_role('admin')
def update_user(user_id):
    """Обновление пользователя"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404
        
        updates = request.json
        if 'name' in updates:
            user.name = updates['name']
        if 'email' in updates:
            user.email = updates['email']
        
        db.commit()
        db.refresh(user)
        
        return jsonify({'success': True, 'data': user.to_dict()}), 200
    except ValueError:
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid user ID format'}}), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/v1/users/<user_id>', methods=['DELETE'])
@require_role('admin')
def delete_user(user_id):
    """Удаление пользователя"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404
        
        user_dict = user.to_dict()
        db.delete(user)
        db.commit()
        
        return jsonify({'success': True, 'data': {'message': 'User deleted', 'deletedUser': user_dict}}), 200
    except ValueError:
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid user ID format'}}), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/v1/users/profile/password', methods=['PUT'])
@require_auth
def change_password():
    """Изменение пароля текущего пользователя"""
    db = SessionLocal()
    try:
        data = request.json
        
        # Валидация
        try:
            password_data = PasswordChange(**data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': str(e.errors()[0]['msg'])
                }
            }), 400
        
        user_id = request.user.get('user_id')
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        # Проверка старого пароля
        if not verify_password(password_data.old_password, user.password_hash):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Old password is incorrect'
                }
            }), 401
        
        # Установка нового пароля
        user.password_hash = hash_password(password_data.new_password)
        db.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Password changed successfully'
            }
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()

@app.route('/v1/users/<user_id>/roles', methods=['PUT'])
@require_role('admin')
def update_user_roles(user_id):
    """Обновление ролей пользователя (только admin)"""
    db = SessionLocal()
    try:
        data = request.json
        
        # Валидация
        try:
            role_data = UserRoleUpdate(**data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': str(e.errors()[0]['msg'])
                }
            }), 400
        
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        user.roles = role_data.roles
        db.commit()
        db.refresh(user)
        
        return jsonify({
            'success': True,
            'data': {
                'user': user.to_dict(),
                'message': 'User roles updated successfully'
            }
        }), 200
    except ValueError:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_UUID',
                'message': 'Invalid user ID format'
            }
        }), 400
    except Exception as e:
        db.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()

@app.route('/v1/users/search', methods=['GET'])
@require_auth
def search_users():
    """Поиск пользователей по имени или email"""
    db = SessionLocal()
    try:
        search_query = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)
        
        if not search_query:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Search query is required (parameter: q)'
                }
            }), 400
        
        if len(search_query) < 2:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Search query must be at least 2 characters'
                }
            }), 400
        
        search_pattern = f'%{search_query}%'
        query = db.query(User).filter(
            (User.name.ilike(search_pattern)) | 
            (User.email.ilike(search_pattern))
        )
        
        total = query.count()
        offset = (page - 1) * per_page
        users = query.offset(offset).limit(per_page).all()
        
        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in users],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()

@app.route('/v1/users/stats', methods=['GET'])
@require_role('admin')
def get_stats():
    """Получение статистики по пользователям (только admin)"""
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        admin_users = db.query(User).filter(User.roles.contains(['admin'])).count()
        regular_users = total_users - admin_users
        
        # Последние зарегистрированные
        recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'admin_users': admin_users,
                'regular_users': regular_users,
                'recent_users': [user.to_dict() for user in recent_users]
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()

if __name__ == '__main__':
    print(f'Users service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
