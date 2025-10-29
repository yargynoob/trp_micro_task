from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 8000))

fake_users_db = {}
current_id = 1

@app.route('/users', methods=['GET'])
def get_users():
    users = list(fake_users_db.values())
    return jsonify(users), 200

@app.route('/users', methods=['POST'])
def create_user():
    global current_id
    user_data = request.json
    user_id = current_id
    current_id += 1
    
    new_user = {'id': user_id, **user_data}
    fake_users_db[user_id] = new_user
    return jsonify(new_user), 201

@app.route('/users/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'OK',
        'service': 'Users Service',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

@app.route('/users/status', methods=['GET'])
def status():
    return jsonify({'status': 'Users service is running'}), 200

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = fake_users_db.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user), 200

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    if user_id not in fake_users_db:
        return jsonify({'error': 'User not found'}), 404
    
    updates = request.json
    updated_user = {**fake_users_db[user_id], **updates}
    fake_users_db[user_id] = updated_user
    return jsonify(updated_user), 200

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if user_id not in fake_users_db:
        return jsonify({'error': 'User not found'}), 404
    
    deleted_user = fake_users_db[user_id]
    del fake_users_db[user_id]
    return jsonify({'message': 'User deleted', 'deletedUser': deleted_user}), 200

if __name__ == '__main__':
    print(f'Users service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
