from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Order
from auth import require_auth, require_role
import uuid
from decimal import Decimal

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 8002))

@app.before_request
def add_request_id():
    """Добавление X-Request-ID к каждому запросу"""
    request.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

@app.route('/orders/status', methods=['GET'])
def status():
    """Status endpoint"""
    return jsonify({'status': 'Orders service is running'}), 200

@app.route('/orders/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'service': 'Orders Service',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

@app.route('/v1/orders/<order_id>', methods=['GET'])
@require_auth
def get_order(order_id):
    """Получение заказа по ID"""
    db = SessionLocal()
    try:
        user_id = request.user.get('user_id')
        user_roles = request.user.get('roles', [])
        
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Order not found'}}), 404
        
        # Проверяем права доступа: пользователь видит только свои заказы
        if 'admin' not in user_roles and str(order.user_id) != user_id:
            return jsonify({'success': False, 'error': {'code': 'FORBIDDEN', 'message': 'Access denied'}}), 403
        
        return jsonify({'success': True, 'data': order.to_dict()}), 200
    except ValueError:
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid order ID format'}}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/v1/orders', methods=['GET'])
@require_auth
def get_orders():
    """Получение списка заказов с фильтрацией по user_id"""
    db = SessionLocal()
    try:
        user_id = request.user.get('user_id')
        user_roles = request.user.get('roles', [])
        
        query = db.query(Order)
        
        # Admin видит все заказы, обычный пользователь - только свои
        if 'admin' not in user_roles:
            query = query.filter(Order.user_id == uuid.UUID(user_id))
        else:
            # Admin может фильтровать по userId
            filter_user_id = request.args.get('userId')
            if filter_user_id:
                try:
                    query = query.filter(Order.user_id == uuid.UUID(filter_user_id))
                except ValueError:
                    return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid user ID format'}}), 400
        
        # Пагинация
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        orders = query.offset(offset).limit(per_page).all()
        return jsonify({'success': True, 'data': [order.to_dict() for order in orders]}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/v1/orders', methods=['POST'])
@require_auth
def create_order():
    """Создание нового заказа"""
    db = SessionLocal()
    try:
        order_data = request.json
        user_id_from_token = request.user.get('user_id')
        
        if not order_data.get('items'):
            return jsonify({'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': 'items are required'}}), 400
        
        # Используем user_id из токена
        total_amount = Decimal('0.00')
        items = order_data.get('items', [])
        for item in items:
            total_amount += Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 0)))
        
        new_order = Order(
            user_id=uuid.UUID(user_id_from_token),
            items=items,
            status='created',
            total_amount=total_amount
        )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        return jsonify({'success': True, 'data': new_order.to_dict()}), 201
    except ValueError as e:
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid user ID format'}}), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/v1/orders/<order_id>', methods=['PUT'])
@require_auth
def update_order(order_id):
    """Обновление заказа"""
    db = SessionLocal()
    try:
        user_id = request.user.get('user_id')
        user_roles = request.user.get('roles', [])
        
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Order not found'}}), 404
        
        if 'admin' not in user_roles and str(order.user_id) != user_id:
            return jsonify({'success': False, 'error': {'code': 'FORBIDDEN', 'message': 'Access denied'}}), 403
        
        order_data = request.json
        
        if 'admin' not in user_roles:
            if 'status' in order_data and order_data['status'] != 'cancelled':
                return jsonify({'success': False, 'error': {'code': 'FORBIDDEN', 'message': 'Only cancellation allowed'}}), 403
            if 'items' in order_data:
                return jsonify({'success': False, 'error': {'code': 'FORBIDDEN', 'message': 'Cannot modify items'}}), 403
        
        if 'status' in order_data:
            order.status = order_data['status']
        if 'items' in order_data and 'admin' in user_roles:
            order.items = order_data['items']
            total_amount = Decimal('0.00')
            for item in order_data['items']:
                total_amount += Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 0)))
            order.total_amount = total_amount
        
        db.commit()
        db.refresh(order)
        
        return jsonify({'success': True, 'data': order.to_dict()}), 200
    except ValueError:
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid order ID format'}}), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/v1/orders/<order_id>', methods=['DELETE'])
@require_role('admin')
def delete_order(order_id):
    """Удаление заказа"""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Order not found'}}), 404
        
        order_dict = order.to_dict()
        db.delete(order)
        db.commit()
        
        return jsonify({'success': True, 'data': {'message': 'Order deleted', 'deletedOrder': order_dict}}), 200
    except ValueError:
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid order ID format'}}), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

if __name__ == '__main__':
    print(f'Orders service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
