from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 8000))

fake_orders_db = {}
current_id = 1

@app.route('/orders/status', methods=['GET'])
def status():
    return jsonify({'status': 'Orders service is running'}), 200

@app.route('/orders/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'OK',
        'service': 'Orders Service',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = fake_orders_db.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify(order), 200

@app.route('/orders', methods=['GET'])
def get_orders():
    orders = list(fake_orders_db.values())
    
    user_id = request.args.get('userId')
    if user_id:
        user_id = int(user_id)
        orders = [order for order in orders if order.get('userId') == user_id]
    
    return jsonify(orders), 200

@app.route('/orders', methods=['POST'])
def create_order():
    global current_id
    order_data = request.json
    order_id = current_id
    current_id += 1
    
    new_order = {'id': order_id, **order_data}
    fake_orders_db[order_id] = new_order
    return jsonify(new_order), 201

@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    if order_id not in fake_orders_db:
        return jsonify({'error': 'Order not found'}), 404
    
    order_data = request.json
    fake_orders_db[order_id] = {'id': order_id, **order_data}
    return jsonify(fake_orders_db[order_id]), 200

@app.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    if order_id not in fake_orders_db:
        return jsonify({'error': 'Order not found'}), 404
    
    deleted_order = fake_orders_db[order_id]
    del fake_orders_db[order_id]
    return jsonify({'message': 'Order deleted', 'deletedOrder': deleted_order}), 200

if __name__ == '__main__':
    print(f'Orders service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
