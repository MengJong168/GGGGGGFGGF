from flask import Flask, request, jsonify
from bakong_khqr import KHQR
from flask_cors import CORS
import json
import os
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from cachetools import TTLCache
import lib2
import json
import asyncio

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize KHQR with your token
khqr = KHQR("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTYzOGFlMDExMGEyNGFkNSJ9LCJpYXQiOjE3NTM2NTg4ODEsImV4cCI6MTc2MTQzNDg4MX0.Zo5tlVnf03XfcgfxKXaYMVP-MAehkUcF61TA-QMzq5E")

# Base data storage directory
BASE_DATA_DIR = 'data'

# Get store-specific file paths
def get_store_files(store_name):
    store_dir = os.path.join(BASE_DATA_DIR, store_name)
    os.makedirs(store_dir, exist_ok=True)
    return {
        'transactions': os.path.join(store_dir, 'transactions.json'),
        'packages': os.path.join(store_dir, 'packages.json')
    }

# Initialize default data for a store if files don't exist
def initialize_store_data(store_name):
    files = get_store_files(store_name)
    
    # Default transactions
    if not os.path.exists(files['transactions']):
        with open(files['transactions'], 'w') as f:
            json.dump({"pending": [], "expired": [], "completed": []}, f, indent=2)
    
    # Default packages
    if not os.path.exists(files['packages']):
        default_packages = {
            "ml": [
                {"name": "11", "price": 0.25},
                {"name": "56", "price": 0.89}
            ],
            "ff": [
                {"name": "25", "price": 0.30},
                {"name": "100", "price": 0.99}
            ],
            "pubg": [
                {"name": "60", "price": 0.99},
                {"name": "325", "price": 4.99},
                {"name": "660", "price": 9.99}
            ],
            "hok": [
                {
                    "name": "16 TOKENS",
                    "price": 0.25,
                    "image": "",
                    "package_id": 302
                }
            ],
            "bloodstrike": [
                {"name": "Elite Pass", "price": 4.10, "image": "bs-elite_pass.jpg", "package_id": 250}
            ],
            "mcgg": [
                {
                    "name": "86 Diamonds",
                    "price": 1.40,
                    "image": "",
                    "package_id": 605
                },
                {
                    "name": "172 Diamonds",
                    "price": 2.60,
                    "image": "",
                    "package_id": 606
                }
            ],
            "ml_special_offers": [
                {"name": "11", "price": 0.20, "image": "ml-diamond.jpg"}
            ],
            "ff_special_offers": [
                {"name": "25", "price": 0.25, "image": "ff-diamond.jpg"}
            ],
            "pubg_special_offers": [
                {"name": "60", "price": 0.89, "image": "pubg-uc.jpg"},
                {"name": "325", "price": 4.49, "image": "pubg-uc.jpg"}
            ],
            "hok_special_offers": [
                {
                    "name": "16 TOKENS",
                    "price": 0.25,
                    "image": "",
                    "package_id": 302
                }
            ],
            "bloodstrike_special_offers": [
                {"name": "Elite Pass", "price": 4.05, "image": "bs-elite_pass.jpg", "package_id": 250}
            ],
            "mcgg_special_offers": [
                {
                    "name": "86+86 Diamonds",
                    "price": 2.50,
                    "image": "mcgg-diamond.jpg",
                    "package_id": 607
                }
            ]
        }
        with open(files['packages'], 'w') as f:
            json.dump(default_packages, f, indent=2)

# Load data from file for a specific store
def load_data(store_name, data_type):
    files = get_store_files(store_name)
    filename = files[data_type]
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save data to file for a specific store
def save_data(store_name, data_type, data):
    files = get_store_files(store_name)
    filename = files[data_type]
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving data for store {store_name}: {e}")
        return False

# Get store name from request parameters with default
def get_store_name():
    store_name = request.args.get('store', 'mengtopup')  # Default to 'mengtopup'
    # Ensure store name is safe for file paths
    store_name = ''.join(c for c in store_name if c.isalnum() or c in ('-', '_')).lower()
    return store_name

# Routes for Transactions
@app.route('/transactions', methods=['GET'])
def get_transactions():
    """Get all transactions for a specific store"""
    store_name = get_store_name()
    initialize_store_data(store_name)
    data = load_data(store_name, 'transactions')
    return jsonify(data)

@app.route('/transactions', methods=['POST'])
def update_transactions():
    """Update transactions (replace entire structure) for a specific store"""
    try:
        store_name = get_store_name()
        initialize_store_data(store_name)
        new_data = request.get_json()
        if save_data(store_name, 'transactions', new_data):
            return jsonify({"success": True, "message": "Transactions updated successfully", "store": store_name})
        else:
            return jsonify({"success": False, "error": "Failed to save transactions", "store": store_name}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "store": store_name}), 400

@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    """Add a single transaction to a specific status category for a store"""
    try:
        store_name = get_store_name()
        initialize_store_data(store_name)
        data = request.get_json()
        status = data.get('status')  # pending, expired, completed
        transaction = data.get('transaction')
        
        if not status or not transaction:
            return jsonify({"success": False, "error": "Missing status or transaction data", "store": store_name}), 400
        
        transactions = load_data(store_name, 'transactions')
        
        # Initialize category if it doesn't exist
        if status not in transactions:
            transactions[status] = []
        
        # Add transaction with timestamp if not present
        if not any(t.get('transaction_id') == transaction.get('transaction_id') for t in transactions[status]):
            if 'timestamp' not in transaction:
                transaction['timestamp'] = datetime.now().isoformat()
            transactions[status].append(transaction)
        
        if save_data(store_name, 'transactions', transactions):
            return jsonify({"success": True, "message": "Transaction added successfully", "store": store_name})
        else:
            return jsonify({"success": False, "error": "Failed to save transaction", "store": store_name}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "store": store_name}), 400

# Routes for Packages
@app.route('/packages', methods=['GET'])
def get_packages():
    """Get all packages for a specific store"""
    store_name = get_store_name()
    initialize_store_data(store_name)
    data = load_data(store_name, 'packages')
    return jsonify(data)

@app.route('/packages', methods=['POST'])
def update_packages():
    """Update packages (replace entire structure) for a specific store"""
    try:
        store_name = get_store_name()
        initialize_store_data(store_name)
        new_data = request.get_json()
        if save_data(store_name, 'packages', new_data):
            return jsonify({"success": True, "message": "Packages updated successfully", "store": store_name})
        else:
            return jsonify({"success": False, "error": "Failed to save packages", "store": store_name}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "store": store_name}), 400

@app.route('/packages/update', methods=['POST'])
def update_single_package():
    """Update a single package price for a specific store"""
    try:
        store_name = get_store_name()
        initialize_store_data(store_name)
        data = request.get_json()
        game_type = data.get('game_type')
        package_name = data.get('package_name')
        new_price = data.get('new_price')
        is_special_offer = data.get('is_special_offer', False)
        
        if not all([game_type, package_name, new_price is not None]):
            return jsonify({"success": False, "error": "Missing required fields", "store": store_name}), 400
        
        packages = load_data(store_name, 'packages')
        section = f"{game_type}_special_offers" if is_special_offer else game_type
        
        if section not in packages:
            return jsonify({"success": False, "error": f"Section {section} not found", "store": store_name}), 404
        
        updated = False
        for item in packages[section]:
            if item.get('name') == package_name:
                item['price'] = float(new_price)
                updated = True
                break
        
        if not updated:
            return jsonify({"success": False, "error": "Package not found", "store": store_name}), 404
        
        if save_data(store_name, 'packages', packages):
            return jsonify({"success": True, "message": "Package updated successfully", "store": store_name})
        else:
            return jsonify({"success": False, "error": "Failed to save package update", "store": store_name}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "store": store_name}), 400

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/check_payment', methods=['GET'])
def check_payment():
    # Get the md5_hash from query parameters
    md5_hash = request.args.get('md5')
    
    if not md5_hash:
        return jsonify({
            'error': 'Missing md5 parameter',
            'message': 'Please provide an md5 hash in the query parameters'
        }), 400
    
    try:
        # Check payment using the KHQR library
        result = khqr.check_payment(md5_hash)
        
        return jsonify({
            'success': True,
            'md5': md5_hash,
            'status': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'An error occurred while checking payment'
        }), 500

# New endpoint to list all available stores
@app.route('/stores', methods=['GET'])
def list_stores():
    """List all available stores"""
    try:
        if not os.path.exists(BASE_DATA_DIR):
            return jsonify({"stores": []})
        
        stores = []
        for item in os.listdir(BASE_DATA_DIR):
            if os.path.isdir(os.path.join(BASE_DATA_DIR, item)):
                stores.append(item)
        
        return jsonify({"stores": stores})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create a cache with a TTL (time-to-live) of 300 seconds (5 minutes)
cache = TTLCache(maxsize=100, ttl=300)

def cached_endpoint(ttl=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = (request.path, tuple(request.args.items()))
            if cache_key in cache:
                return cache[cache_key]
            else:
                result = func(*args, **kwargs)
                cache[cache_key] = result
                return result
        return wrapper
    return decorator



# curl -X GET 'http://127.0.0.1:3000/api/account?uid=1813014615&region=ind'
@app.route('/api/account')
@cached_endpoint()
def get_account_info():
    region = request.args.get('region')
    uid = request.args.get('uid')
    
    if not uid:
        response = {
            "error": "Invalid request",
            "message": "Empty 'uid' parameter. Please provide a valid 'uid'."
        }
        return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}

    if not region:
        response = {
            "error": "Invalid request",
            "message": "Empty 'region' parameter. Please provide a valid 'region'."
        }
        return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}

    return_data = asyncio.run(lib2.GetAccountInformation(uid, "7", region, "/GetPlayerPersonalShow"))
    formatted_json = json.dumps(return_data, indent=2, ensure_ascii=False)
    return formatted_json, 200, {'Content-Type': 'application/json; charset=utf-8'}

if __name__ == '__main__':
    # Initialize default store on startup
    initialize_store_data('mengtopup')
    print("Data Store Server starting...")
    print("Available endpoints:")
    print("  GET  /transactions?store=<store_name> - Get all transactions for a store")
    print("  POST /transactions?store=<store_name> - Replace all transactions for a store")
    print("  POST /transactions/add?store=<store_name> - Add a single transaction for a store")
    print("  GET  /packages?store=<store_name> - Get all packages for a store")
    print("  POST /packages?store=<store_name> - Replace all packages for a store")
    print("  POST /packages/update?store=<store_name> - Update a single package price for a store")
    print("  GET  /health - Health check")
    print("  GET  /stores - List all available stores")
    print("  GET  /api/check_payment?md5=<hash> - Check payment status")
    
    app.run()
