from flask import Flask, request, jsonify
from pymongo import MongoClient
import uuid
import os
import bcrypt
from flask_cors import CORS
from collections import defaultdict 

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app)
client = MongoClient('mongodb+srv://aryanbasu005:Qwerty1234@devdataset.6ghws.mongodb.net/splitwise?retryWrites=true&w=majority')
db = client  
@app.route("/")
def home():
    try:
    
        listings_collection = db.users  # Collection
        
        # Fetch one document for demonstration
        # listing = listings_collection.find_one({'_id': '10006546'})
        
        # Convert the document to a string to display (handle None if no data exists)
        return f"Home Page! Example Listing: {listing if listing else 'No listing found'}"
    
    except Exception as e:
        return f"An error occurred: {e}"

@app.route('/login', methods=['POST'])
def login_user():
    try:
        # Extract email and password from the request body
        data = request.json
        email = data['email']
        password = data['password']
        
        # Fetch the user from the database
        splitwiseocollection=db.splitwise
        usercollection=splitwiseocollection.users
        user = usercollection.find_one({"email": email})
        
        if not user:
            return jsonify({"message": "Invalid email or password!"}), 401
        
        # Check if the provided password matches the stored hashed password
        stored_hashed_password = user["password"].encode('utf-8')  # Ensure it's bytes
        if not bcrypt.checkpw(password.encode('utf-8'), eval(stored_hashed_password)):
            return jsonify({"message": "Invalid email or password!"}), 401

        # Authentication successful
        return jsonify({
            "message": "Login successful!",
            "user_id": user["_id"],
            "name": user["name"],
            "email": user["email"]
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/register_user', methods=['POST'])
def register_user():
    try:
        data = request.json
        name = data['name']
        email = data['email']
        password=data['password']
        salt = bcrypt.gensalt(rounds=15)
        hashed_password = str(bcrypt.hashpw(password.encode('utf-8'), bytes(salt)))
        
        # Generate a unique user ID
        user_id = f'{uuid.uuid4()}'
    
        splitwiseocollection=db.splitwise
        usercollection=splitwiseocollection.users
        # Check if the email already exists
        existing_user = usercollection.find_one({"email": email})
        if existing_user:
            return jsonify({"message": "User with this email already exists!"}), 400

        # Create user record
        user = {
            "_id": user_id,
            "name": name,
            "email": email,
            "password":hashed_password,
            "friends": []  # Initialize empty friend list
        }
        usercollection.insert_one(user)

        return jsonify({"message": "User registered successfully!", "user_id": user_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/add_transaction', methods=['POST'])
def add_transaction():

    try:
        # Parse input data
       
        data = request.json
        description = data['description']
        amount = data['amount']
        paid_by = data['paid_by']  # Unique user ID
        split_among = data['split_among']  # List of unique user IDs
        split_type = data['split_type']  # Split type (e.g., 'equal', 'exact')
        
        # Calculate split details
        split_details = {}
        if split_type == "equal":
            split_amount = amount / len(split_among)
            split_details = {user: split_amount for user in split_among}
        elif split_type == "exact":
            split_details = data.get('split_details', {})  # Must be provided in this case

        # Generate unique transaction ID
        txn_id = str(uuid.uuid4())
        
        # Create transaction record
        transaction = {
            "_id": txn_id,
            "description": description,
            "amount": amount,
            "paid_by": paid_by,
            "split_among": split_among,
            "split_type": split_type,
            "split_details": split_details,
            "date":'22 june'
        }
        splitwiseocollection=db.splitwise
        splitwiseocollection.transactions.insert_one(transaction)
        return jsonify({"message": "Transaction added successfully!", "transaction_id": txn_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/balance/<user_id>', methods=['GET'])
def get_user_balance(user_id):
    try:
        # Database collections
        print(uuid.uuid4())
        splitwiseocollection=db.splitwise
        transactions_collection = splitwiseocollection.transactions
        users_collection = splitwiseocollection.users

        # Fetch transactions involving the user
        transactions = list(transactions_collection.find({
            "$or": [
                {"paid_by": user_id},
                {"split_among": {"$in": [user_id]}}
            ]
        }))

        if not transactions:
            return jsonify({"message": "No transactions found for this user."}), 404

        # Calculate balances with friends
        print(transactions)
        balance_map = defaultdict(lambda: {"relation": None, "amount": 0})
        for txn in transactions:
            if txn["paid_by"] == user_id:
                # User is the payer, others owe them
                
                for friend_id, amount in txn["split_details"].items():
                    if friend_id != user_id:  # Exclude self from balance calculations
                        balance_map[friend_id]["relation"] = "lend"
                        balance_map[friend_id]["amount"] += amount
            elif user_id in txn["split_among"]:
                
                # User is part of the split, they owe the payer
                payer_id = txn["paid_by"]
                balance_map[payer_id]["relation"] = "owe"
                balance_map[payer_id]["amount"] += txn["split_details"][user_id]
                

        # Fetch details of friends involved
        friend_ids = list(balance_map.keys())
        # print(friend_ids)
        friends = list(users_collection.find({"_id": {"$in": friend_ids}}))
        print(friends)
        friend_details = {
            str(friend["_id"]): {"name": friend["name"], "email": friend["email"]}
            for friend in friends
        }

        # Prepare response
        balances = []
        for friend_id, balance_info in balance_map.items():
            balances.append({
                "friend_id": friend_id,
                "name": friend_details.get(friend_id, {}).get("name", "Unknown"),
                "email": friend_details.get(friend_id, {}).get("email", "Unknown"),
                "relation": balance_info["relation"],
                "amount": balance_info["amount"]
            })

        return jsonify({
            "user_id": user_id,
            "balances": balances
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    try:
        # Extract user_id from the header
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "user_id header is missing"}), 400

        # Fetch collections
        splitwise_collection = db.splitwise
        user_collection = splitwise_collection.users

        # Get the current user's friends list
        current_user = user_collection.find_one({"_id": user_id}, {"friends": 1})
        if not current_user:
            return jsonify({"error": "Current user not found"}), 404

        friends = current_user.get("friends", [])

        # Fetch all users excluding the current user
        users = user_collection.find(
            {"_id": {"$ne": user_id}},
            {"_id": 1, "user_id": 1, "name": 1, "email": 1}
        )

        # Convert to a list of dictionaries and add `is_friend` field
        user_list = []
        for user in users:
            user["_id"] = str(user["_id"])  # Convert ObjectId to string if necessary
            user["is_friend"] = user["_id"] in friends
            user_list.append(user)

        # Check if users exist
        if not user_list:
            return jsonify({"message": "No users found."}), 404

        return jsonify({"users": user_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/addfriends/<user_id>', methods=['POST'])
def add_friend(user_id):
    try:
        # Extract current user's ID from the header
        current_user_id = request.headers.get('user-id')
     
        if not current_user_id:
            return jsonify({"error": "user_id header is missing"}), 400

        # Fetch collections
        splitwise_collection = db.splitwise
        user_collection = splitwise_collection.users

        # Check if the current user exists
        current_user = user_collection.find_one({"_id": current_user_id})
        if not current_user:
            return jsonify({"error": "Current user not found"}), 404

        # Check if the user to be added as a friend exists
        friend_user = user_collection.find_one({"_id": user_id})
        if not friend_user:
            return jsonify({"error": f"User with id {user_id} not found"}), 404

        # Check if the user is already a friend of the current user
        if user_id in current_user.get("friends", []):
            return jsonify({"message": "This user is already a friend"}), 400

        # Add the user to the current user's friends array
        user_collection.update_one(
            {"_id": current_user_id},
            {"$addToSet": {"friends": user_id}}  # Ensures no duplicates
        )

        # Add the current user to the target user's friends array
        user_collection.update_one(
            {"_id": user_id},
            {"$addToSet": {"friends": current_user_id}}  # Ensures no duplicates
        )

        return jsonify({"message": f"User {user_id} and {current_user_id} are now friends"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/search_user', methods=['GET'])
def search_user_by_email():
    try:
        # Get the email from query parameters
        email = request.args.get('email')
        
        if not email:
            return jsonify({"error": "Email parameter is required."}), 400

        # Search for the user by email
        splitwiseocollection=db.splitwise
        user_collection=splitwiseocollection.users
        users = list(user_collection.find(
            {"email": {"$regex": email, "$options": "i"}},  # Case-insensitive match
            {"_id": 0, "user_id": 1, "name": 1, "email": 1}  # Exclude `_id`, include other fields
        ))

        # If user is not found
        if not users:
            return jsonify({"message": "User not found."}), 404

        return jsonify({"user": users}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__": 
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port, debug=True)

