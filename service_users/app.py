from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import User
import uuid

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 8001))

def get_db():
    """Получение сессии БД"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass

@app.route('/users', methods=['GET'])
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

@app.route('/users', methods=['POST'])
def create_user():
    """Создание нового пользователя (базовая версия без валидации)"""
    db = SessionLocal()
    try:
        user_data = request.json
        
        if not user_data.get('email') or not user_data.get('name'):
            return jsonify({'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': 'Email and name are required'}}), 400
        
        existing_user = db.query(User).filter(User.email == user_data['email']).first()
        if existing_user:
            return jsonify({'success': False, 'error': {'code': 'EMAIL_EXISTS', 'message': 'User with this email already exists'}}), 400
        
        new_user = User(
            email=user_data['email'],
            name=user_data['name'],
            password_hash='temporary_hash',
            roles=['user']
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return jsonify({'success': True, 'data': new_user.to_dict()}), 201
    except Exception as e:
        db.rollback()
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

@app.route('/users/<user_id>', methods=['GET'])
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

@app.route('/users/<user_id>', methods=['PUT'])
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

@app.route('/users/<user_id>', methods=['DELETE'])
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
