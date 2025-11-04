from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import User
from auth import hash_password, verify_password, create_access_token, require_auth, require_role
from schemas import UserRegister, UserLogin
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
    """Получение списка всех пользователей"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return jsonify({'success': True, 'data': [user.to_dict() for user in users]}), 200
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

if __name__ == '__main__':
    print(f'Users service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
