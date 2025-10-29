from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from datetime import datetime, timedelta
import threading

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 8000))
USERS_SERVICE_URL = 'http://service_users:8000'
ORDERS_SERVICE_URL = 'http://service_orders:8000'

class CircuitBreaker:
    def __init__(self, timeout=3, error_threshold=0.5, reset_timeout=3):
        self.timeout = timeout
        self.error_threshold = error_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = 'closed'
        self.lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        with self.lock:
            if self.state == 'open':
                if datetime.now() - self.last_failure_time > timedelta(seconds=self.reset_timeout):
                    self.state = 'half_open'
                    print(f'Circuit breaker half-open')
                else:
                    raise Exception('Circuit breaker is open')
        
        try:
            result = func(*args, **kwargs)
            with self.lock:
                self.success_count += 1
                if self.state == 'half_open':
                    self.state = 'closed'
                    self.failure_count = 0
                    print(f'Circuit breaker closed')
            return result
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = datetime.now()
                total = self.failure_count + self.success_count
                if total > 0 and self.failure_count / total >= self.error_threshold:
                    self.state = 'open'
                    print(f'Circuit breaker opened')
            raise e

users_circuit = CircuitBreaker()
orders_circuit = CircuitBreaker()

def call_users_service(url, method='GET', data=None):
    try:
        response = requests.request(method, url, json=data, timeout=3)
        if response.status_code == 404:
            return response.json(), response.status_code
        response.raise_for_status()
        return response.json(), response.status_code
    except Exception as e:
        raise e

def call_orders_service(url, method='GET', data=None):
    try:
        response = requests.request(method, url, json=data, timeout=3)
        if response.status_code == 404:
            return response.json(), response.status_code
        response.raise_for_status()
        return response.json(), response.status_code
    except Exception as e:
        raise e

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/users/{user_id}')
        return jsonify(result), status
    except:
        return jsonify({'error': 'Users service temporarily unavailable'}), 500

@app.route('/users', methods=['POST'])
def create_user():
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/users', 'POST', request.json)
        return jsonify(result), status
    except:
        return jsonify({'error': 'Users service temporarily unavailable'}), 500

@app.route('/users', methods=['GET'])
def get_users():
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/users')
        return jsonify(result), status
    except:
        return jsonify({'error': 'Users service temporarily unavailable'}), 500

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/users/{user_id}', 'DELETE')
        return jsonify(result), status
    except:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        result, status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/users/{user_id}', 'PUT', request.json)
        return jsonify(result), status
    except:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/orders/{order_id}')
        return jsonify(result), status
    except:
        return jsonify({'error': 'Orders service temporarily unavailable'}), 500

@app.route('/orders', methods=['POST'])
def create_order():
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/orders', 'POST', request.json)
        return jsonify(result), status
    except:
        return jsonify({'error': 'Orders service temporarily unavailable'}), 500

@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/orders')
        return jsonify(result), status
    except:
        return jsonify({'error': 'Orders service temporarily unavailable'}), 500

@app.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/orders/{order_id}', 'DELETE')
        return jsonify(result), status
    except:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    try:
        result, status = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/orders/{order_id}', 'PUT', request.json)
        return jsonify(result), status
    except:
        return jsonify({'error': 'Internal server error'}), 500

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

@app.route('/users/<int:user_id>/details', methods=['GET'])
def get_user_details(user_id):
    try:
        user_result, user_status = users_circuit.call(call_users_service, f'{USERS_SERVICE_URL}/users/{user_id}')
        if user_status == 404:
            return jsonify(user_result), user_status
        
        orders_result, _ = orders_circuit.call(call_orders_service, f'{ORDERS_SERVICE_URL}/orders')
        user_orders = [order for order in orders_result if order.get('userId') == user_id]
        
        return jsonify({'user': user_result, 'orders': user_orders}), 200
    except:
        return jsonify({'error': 'Internal server error'}), 500

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
