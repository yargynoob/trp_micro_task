from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Order
from auth import require_auth, require_role
from schemas import OrderCreate, OrderUpdate, OrderStatusUpdate, OrderSearch
from pydantic import ValidationError
from logger import logger, log_request, log_response
import uuid
from decimal import Decimal
from sqlalchemy import func, and_, or_

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 8002))

@app.before_request
def before_request():
    """Обработка запроса до маршрутизации"""
    request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    g.request_id = request_id
    request.request_id = request_id
    log_request()

@app.after_request
def after_request(response):
    """Обработка ответа"""
    return log_response(response)

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
    """Получение списка заказов с фильтрацией и пагинацией"""
    db = SessionLocal()
    try:
        user_id = request.user.get('user_id')
        user_roles = request.user.get('roles', [])
        
        query = db.query(Order)
        
        if 'admin' not in user_roles:
            query = query.filter(Order.user_id == uuid.UUID(user_id))
        else:
            filter_user_id = request.args.get('userId')
            if filter_user_id:
                try:
                    query = query.filter(Order.user_id == uuid.UUID(filter_user_id))
                except ValueError:
                    return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid user ID format'}}), 400
        
        status_filter = request.args.get('status')
        if status_filter:
            query = query.filter(Order.status == status_filter)
        
        min_amount = request.args.get('min_amount')
        if min_amount:
            try:
                query = query.filter(Order.total_amount >= Decimal(min_amount))
            except:
                pass
        
        max_amount = request.args.get('max_amount')
        if max_amount:
            try:
                query = query.filter(Order.total_amount <= Decimal(max_amount))
            except:
                pass
        
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        if sort_by == 'created_at':
            query = query.order_by(Order.created_at.desc() if sort_order == 'desc' else Order.created_at.asc())
        elif sort_by == 'total_amount':
            query = query.order_by(Order.total_amount.desc() if sort_order == 'desc' else Order.total_amount.asc())
        else:
            query = query.order_by(Order.created_at.desc())
        
        total = query.count()
        
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)
        offset = (page - 1) * per_page
        
        orders = query.offset(offset).limit(per_page).all()
        
        return jsonify({
            'success': True,
            'data': [order.to_dict() for order in orders],
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

@app.route('/v1/orders', methods=['POST'])
@require_auth
def create_order():
    """Создание нового заказа"""
    db = SessionLocal()
    try:
        order_data = request.json
        user_id_from_token = request.user.get('user_id')
        
        try:
            order_create = OrderCreate(**order_data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': str(e.errors()[0]['msg'])
                }
            }), 400
        
        total_amount = Decimal('0.00')
        items = [item.dict() for item in order_create.items]
        for item in items:
            total_amount += Decimal(str(item['price'])) * Decimal(str(item['quantity']))
        
        new_order = Order(
            user_id=uuid.UUID(user_id_from_token),
            items=items,
            status='created',
            total_amount=total_amount
        )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        logger.info(
            'Order created successfully',
            order_id=str(new_order.id),
            user_id=str(new_order.user_id),
            total_amount=float(new_order.total_amount),
            items_count=len(items)
        )
        
        return jsonify({'success': True, 'data': new_order.to_dict()}), 201
    except ValueError as e:
        logger.warning('Invalid UUID format', user_id=user_id_from_token)
        return jsonify({'success': False, 'error': {'code': 'INVALID_UUID', 'message': 'Invalid user ID format'}}), 400
    except Exception as e:
        db.rollback()
        logger.error('Order creation failed', exc_info=e, user_id=user_id_from_token)
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

@app.route('/v1/orders/<order_id>/status', methods=['PUT'])
@require_auth
def update_order_status(order_id):
    """Обновление только статуса заказа"""
    db = SessionLocal()
    try:
        user_id = request.user.get('user_id')
        user_roles = request.user.get('roles', [])
        data = request.json
        
        try:
            status_update = OrderStatusUpdate(**data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': str(e.errors()[0]['msg'])
                }
            }), 400
        
        order = db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Order not found'
                }
            }), 404
        
        if 'admin' not in user_roles and str(order.user_id) != user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Access denied'
                }
            }), 403
        
        if 'admin' not in user_roles and status_update.status != 'cancelled':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Only cancellation is allowed for regular users'
                }
            }), 403
        
        old_status = order.status
        order.status = status_update.status
        db.commit()
        db.refresh(order)
        
        logger.info(
            'Order status updated',
            order_id=str(order.id),
            user_id=user_id,
            old_status=old_status,
            new_status=order.status,
            updated_by='admin' if 'admin' in user_roles else 'user'
        )
        
        return jsonify({
            'success': True,
            'data': order.to_dict()
        }), 200
    except ValueError:
        logger.warning('Invalid order UUID', order_id=order_id)
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_UUID',
                'message': 'Invalid order ID format'
            }
        }), 400
    except Exception as e:
        db.rollback()
        logger.error('Order status update failed', exc_info=e, order_id=order_id)
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
    finally:
        db.close()

@app.route('/v1/orders/stats', methods=['GET'])
@require_role('admin')
def get_order_stats():
    """Получение статистики по заказам (только admin)"""
    db = SessionLocal()
    try:
        total_orders = db.query(Order).count()
        
        created_count = db.query(Order).filter(Order.status == 'created').count()
        processing_count = db.query(Order).filter(Order.status == 'processing').count()
        completed_count = db.query(Order).filter(Order.status == 'completed').count()
        cancelled_count = db.query(Order).filter(Order.status == 'cancelled').count()
        
        total_revenue = db.query(func.sum(Order.total_amount)).filter(Order.status == 'completed').scalar() or 0
        avg_order_value = db.query(func.avg(Order.total_amount)).scalar() or 0
        
        recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'data': {
                'total_orders': total_orders,
                'by_status': {
                    'created': created_count,
                    'processing': processing_count,
                    'completed': completed_count,
                    'cancelled': cancelled_count
                },
                'revenue': {
                    'total': float(total_revenue),
                    'average_order_value': float(avg_order_value)
                },
                'recent_orders': [order.to_dict() for order in recent_orders]
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

@app.route('/v1/orders/my-stats', methods=['GET'])
@require_auth
def get_my_order_stats():
    """Получение статистики по своим заказам"""
    db = SessionLocal()
    try:
        user_id = request.user.get('user_id')
        
        query = db.query(Order).filter(Order.user_id == uuid.UUID(user_id))
        
        total_orders = query.count()
        created_count = query.filter(Order.status == 'created').count()
        processing_count = query.filter(Order.status == 'processing').count()
        completed_count = query.filter(Order.status == 'completed').count()
        cancelled_count = query.filter(Order.status == 'cancelled').count()
        
        total_spent = query.filter(Order.status == 'completed').with_entities(func.sum(Order.total_amount)).scalar() or 0
        
        recent_orders = query.order_by(Order.created_at.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'data': {
                'total_orders': total_orders,
                'by_status': {
                    'created': created_count,
                    'processing': processing_count,
                    'completed': completed_count,
                    'cancelled': cancelled_count
                },
                'total_spent': float(total_spent),
                'recent_orders': [order.to_dict() for order in recent_orders]
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
    print(f'Orders service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
