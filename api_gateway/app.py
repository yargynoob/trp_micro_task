from flask import Flask, request, jsonify, g
from flask_cors import CORS
import requests
import os
import uuid
from datetime import datetime
from auth_middleware import require_auth, add_auth_headers, is_public_route
from logger import logger, log_request, log_response
from rate_limiter import rate_limit, global_limiter, auth_limiter, order_creation_limiter
from circuit_breaker import CircuitBreaker

app = Flask(__name__)
CORS(app)

@app.before_request
def before_request():
    """Обработка запроса до маршрутизации"""
    # Генерируем или получаем request_id
    request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    g.request_id = request_id
    request.environ['HTTP_X_REQUEST_ID'] = request_id
    
    # Логируем запрос
    log_request()

@app.after_request
def after_request(response):
    """Обработка ответа"""
    return log_response(response)

PORT = int(os.environ.get('PORT', 8000))
USERS_SERVICE_URL = os.environ.get('USERS_SERVICE_URL', 'http://service_users:8001')
ORDERS_SERVICE_URL = os.environ.get('ORDERS_SERVICE_URL', 'http://service_orders:8002')

# Создаем улучшенные Circuit Breakers
users_circuit = CircuitBreaker('users_service', timeout=3, error_threshold=0.5, reset_timeout=10)
orders_circuit = CircuitBreaker('orders_service', timeout=3, error_threshold=0.5, reset_timeout=10)

def call_users_service(url, method='GET', data=None):
    try:
        headers = add_auth_headers()
        logger.debug('Calling users service', url=url, method=method)
        response = requests.request(method, url, json=data, headers=headers, timeout=3)
        
        logger.info(
            'Users service response',
            url=url,
            method=method,
            status_code=response.status_code,
            response_time=response.elapsed.total_seconds()
        )
        
        if response.status_code == 404:
            return response.json(), response.status_code
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(
            'Users service request failed',
            exc_info=e,
            url=url,
            method=method
        )
        raise e
    except Exception as e:
        logger.error('Unexpected error calling users service', exc_info=e)
        raise e

def call_orders_service(url, method='GET', data=None):
    try:
        headers = add_auth_headers()
        logger.debug('Calling orders service', url=url, method=method)
        response = requests.request(method, url, json=data, headers=headers, timeout=3)
        
        logger.info(
            'Orders service response',
            url=url,
            method=method,
            status_code=response.status_code,
            response_time=response.elapsed.total_seconds()
        )
        if response.status_code == 404:
            return response.json(), response.status_code
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(
            'Orders service request failed',
            exc_info=e,
            url=url,
            method=method
        )
        raise e
    except Exception as e:
        logger.error('Unexpected error calling orders service', exc_info=e)
        raise e

@app.route('/v1/users/register', methods=['POST'])
@rate_limit(auth_limiter)
def register():
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/register', 'POST', request.json)
        return jsonify(result), status
    except Exception as e:
        logger.error('Register endpoint failed', exc_info=e)
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/login', methods=['POST'])
@rate_limit(auth_limiter)
def login():
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/login', 'POST', request.json)
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/profile', methods=['GET'])
@require_auth
def get_profile():
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/profile')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/profile', methods=['PUT'])
@require_auth
def update_profile():
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/profile', 'PUT', request.json)
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/<user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/{user_id}')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users', methods=['GET'])
@require_auth
def get_users():
    try:
        query_string = ''
        if request.args:
            params = []
            if request.args.get('page'):
                params.append(f"page={request.args.get('page')}")
            if request.args.get('per_page'):
                params.append(f"per_page={request.args.get('per_page')}")
            if request.args.get('query'):
                params.append(f"query={request.args.get('query')}")
            if request.args.get('role'):
                params.append(f"role={request.args.get('role')}")
            if params:
                query_string = '?' + '&'.join(params)
        
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users{query_string}')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/<user_id>', methods=['DELETE'])
@require_auth
def delete_user(user_id):
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/{user_id}', 'DELETE')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/<user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/{user_id}', 'PUT', request.json)
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/profile/password', methods=['PUT'])
@require_auth
def change_password():
    """Изменение пароля"""
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/profile/password', 'PUT', request.json)
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/<user_id>/roles', methods=['PUT'])
@require_auth
def update_user_roles(user_id):
    """Обновление ролей"""
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/{user_id}/roles', 'PUT', request.json)
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/search', methods=['GET'])
@require_auth
def search_users():
    """Поиск пользователей"""
    try:
        query_string = ''
        if request.args:
            params = []
            if request.args.get('q'):
                params.append(f"q={request.args.get('q')}")
            if request.args.get('page'):
                params.append(f"page={request.args.get('page')}")
            if request.args.get('per_page'):
                params.append(f"per_page={request.args.get('per_page')}")
            if params:
                query_string = '?' + '&'.join(params)
        
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/search{query_string}')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/users/stats', methods=['GET'])
@require_auth
def get_user_stats():
    """Статистика пользователей"""
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/stats')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Users service temporarily unavailable'}}), 503

@app.route('/v1/orders/<order_id>', methods=['GET'])
@require_auth
def get_order(order_id):
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders/{order_id}')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Orders service temporarily unavailable'}}), 503

@app.route('/v1/orders', methods=['POST'])
@require_auth
@rate_limit(order_creation_limiter)
def create_order():
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders', 'POST', request.json)
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Orders service temporarily unavailable'}}), 503

@app.route('/v1/orders', methods=['GET'])
@require_auth
def get_orders():
    try:
        query_string = ''
        if request.args:
            params = []
            if request.args.get('page'):
                params.append(f"page={request.args.get('page')}")
            if request.args.get('per_page'):
                params.append(f"per_page={request.args.get('per_page')}")
            if request.args.get('userId'):
                params.append(f"userId={request.args.get('userId')}")
            if request.args.get('status'):
                params.append(f"status={request.args.get('status')}")
            if request.args.get('min_amount'):
                params.append(f"min_amount={request.args.get('min_amount')}")
            if request.args.get('max_amount'):
                params.append(f"max_amount={request.args.get('max_amount')}")
            if request.args.get('sort_by'):
                params.append(f"sort_by={request.args.get('sort_by')}")
            if request.args.get('sort_order'):
                params.append(f"sort_order={request.args.get('sort_order')}")
            if params:
                query_string = '?' + '&'.join(params)
        
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders{query_string}')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Orders service temporarily unavailable'}}), 503

@app.route('/v1/orders/<order_id>', methods=['DELETE'])
@require_auth
def delete_order(order_id):
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders/{order_id}', 'DELETE')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Orders service temporarily unavailable'}}), 503

@app.route('/v1/orders/<order_id>', methods=['PUT'])
@require_auth
def update_order(order_id):
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders/{order_id}', 'PUT', request.json)
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Orders service temporarily unavailable'}}), 503

@app.route('/v1/orders/<order_id>/status', methods=['PUT'])
@require_auth
def update_order_status(order_id):
    """Обновление только статуса заказа"""
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders/{order_id}/status', 'PUT', request.json)
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Orders service temporarily unavailable'}}), 503

@app.route('/v1/orders/stats', methods=['GET'])
@require_auth
def get_order_stats():
    """Статистика заказов (admin)"""
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders/stats')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Orders service temporarily unavailable'}}), 503

@app.route('/v1/orders/my-stats', methods=['GET'])
@require_auth
def get_my_order_stats():
    """Статистика своих заказов"""
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders/my-stats')
        return jsonify(result), status
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Orders service temporarily unavailable'}}), 503

@app.route('/orders/status', methods=['GET'])
def orders_status():
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/orders/status')
        return jsonify(result), status
    except:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/health', methods=['GET'])
def orders_health():
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/orders/health')
        return jsonify(result), status
    except:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def gateway_health():
    """Проверка здоровья API Gateway"""
    health_status = {
        'status': 'OK',
        'service': 'API Gateway',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'circuit_breakers': {
            'users_service': users_circuit.get_stats(),
            'orders_service': orders_circuit.get_stats()
        }
    }
    return jsonify(health_status), 200

@app.route('/metrics', methods=['GET'])
@require_auth
def get_metrics():
    """Получение метрик системы (требует аутентификации)"""
    metrics = {
        'success': True,
        'data': {
            'circuit_breakers': {
                'users_service': users_circuit.get_stats(),
                'orders_service': orders_circuit.get_stats()
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    }
    return jsonify(metrics), 200

@app.route('/v1/users/<user_id>/details', methods=['GET'])
@require_auth
def get_user_details(user_id):
    try:
        user_result, user_status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/v1/users/{user_id}')
        if user_status == 404:
            return jsonify(user_result), user_status
        
        orders_result, _ = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/v1/orders?userId={user_id}')
        
        user_data = user_result.get('data', user_result) if isinstance(user_result, dict) else user_result
        orders_data = orders_result.get('data', []) if isinstance(orders_result, dict) else orders_result
        
        return jsonify({'success': True, 'data': {'user': user_data, 'orders': orders_data}}), 200
    except:
        return jsonify({'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Service temporarily unavailable'}}), 503

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'API Gateway is running',
        'circuits': {
            'users': {
                'status': users_circuit.state,
                'stats': {
                    'failures': users_circuit.failure_count,
                    'successes': users_circuit.success_count
                }
            },
            'orders': {
                'status': orders_circuit.state,
                'stats': {
                    'failures': orders_circuit.failure_count,
                    'successes': orders_circuit.success_count
                }
            }
        }
    }), 200

@app.route('/status', methods=['GET'])
def status():
    return jsonify({'status': 'API Gateway is running'}), 200

if __name__ == '__main__':
    print(f'API Gateway running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
