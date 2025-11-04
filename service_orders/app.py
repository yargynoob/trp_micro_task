from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Order
import uuid
from decimal import Decimal

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 8002))

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

@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Получение заказа по ID"""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Order not found'}}), 404
        return jsonify({'success': True, 'data': order.to_dict()}), 200
    except ValueError:
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid order ID format'}}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/orders', methods=['GET'])
def get_orders():
    """Получение списка заказов с фильтрацией по user_id"""
    db = SessionLocal()
    try:
        query = db.query(Order)
        
        user_id = request.args.get('userId')
        if user_id:
            try:
                query = query.filter(Order.user_id == uuid.UUID(user_id))
            except ValueError:
                return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid user ID format'}}), 400
        
        orders = query.all()
        return jsonify({'success': True, 'data': [order.to_dict() for order in orders]}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
    finally:
        db.close()

@app.route('/orders', methods=['POST'])
def create_order():
    """Создание нового заказа"""
    db = SessionLocal()
    try:
        order_data = request.json
        
        if not order_data.get('user_id') or not order_data.get('items'):
            return jsonify({'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': 'user_id and items are required'}}), 400
        
        total_amount = Decimal('0.00')
        items = order_data.get('items', [])
        for item in items:
            total_amount += Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 0)))
        
        new_order = Order(
            user_id=uuid.UUID(order_data['user_id']),
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

@app.route('/orders/<order_id>', methods=['PUT'])
def update_order(order_id):
    """Обновление заказа"""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Order not found'}}), 404
        
        order_data = request.json
        
        if 'status' in order_data:
            order.status = order_data['status']
        if 'items' in order_data:
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

@app.route('/orders/<order_id>', methods=['DELETE'])
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
