from flask import Flask, request, jsonify
from pymongo import MongoClient
import uuid
import os
import bcrypt
from flask_cors import CORS
from collections import defaultdict 
from datetime import datetime,timedelta


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
        splitwise_collection = db.splitwise
        user_collection = splitwise_collection.users
        user = user_collection.find_one({"email": email})
        
        if not user:
            return jsonify({"message": "Invalid email or password!"}), 401
        
        # Check if the provided password matches the stored hashed password
        stored_hashed_password = user["password"].encode('utf-8')  # Ensure it's bytes
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
            return jsonify({"message": "Invalid email or password!"}), 401

        # Authentication successful
        return jsonify({
            "message": "Login successful!",
            "user_id": user["_id"],
            "name": user["name"],
            "email": user["email"],
            "profile_pic":user["profile_pic"]
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/register_user', methods=['POST'])
def register_user():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        profile_pic = data.get('profile_pic', None)  # Optional profile pic from Google
        password = data.get('password')  # Optional, in case of regular registration
        
        splitwise_collection = db.splitwise
        user_collection = splitwise_collection.users

        # Check if the user already exists
        existing_user = user_collection.find_one({"email": email})

        if existing_user:
            # Update profile pic if missing
            if 'profile_pic' not in existing_user or not existing_user['profile_pic']:
                user_collection.update_one(
                    {"_id": existing_user["_id"]},
                    {"$set": {"profile_pic": profile_pic}}
                )
                return jsonify({
                    "message": "User exists. Profile picture updated.",
                    "user_id": existing_user["_id"],
                    "profile_pic":existing_user["profile_pic"]
            
                }), 200

            return jsonify({
                "message": "User with this email already exists!",
                "user_id": existing_user["_id"],
                "profile_pic":existing_user["profile_pic"]
            }), 200

        # If user doesn't exist, proceed with registration
        if not password:
            return jsonify({"message": "Password is required for new user registration!"}), 400

        salt = bcrypt.gensalt(rounds=15)
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Generate a unique user ID
        user_id = str(uuid.uuid4())

        # Create new user record
        user = {
            "_id": user_id,
            "name": name,
            "email": email,
            "password": hashed_password,
            "profile_pic": profile_pic,  # Store the profile pic
            "friends": []  # Initialize empty friend list
        }
        user_collection.insert_one(user)

        return jsonify({
            "message": "User registered successfully!",
            "user_id": user_id,
            "profile_pic":profile_pic
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/friends', methods=['GET'])
def get_friends():
    try:
        # Get the user-id from headers
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "user-id header is required"}), 400

        # Fetch the user from the database
        splitwiseocollection=db.splitwise
        user_collection=splitwiseocollection.users
        user = user_collection.find_one({"_id": user_id})
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get friends array from the user document
        friend_ids = user.get("friends", [])
        
        # Fetch additional info for each friend
        friends_info = []
        for friend_id in friend_ids:
            friend = user_collection.find_one({"_id": friend_id}, {"_id": 1, "name": 1, "email": 1,"profile_pic":1})
            if friend:
                friends_info.append({
                    "friend_id": friend["_id"],
                    "name": friend["name"],
                    "email": friend["email"],
                    "profile_pic":friend["profile_pic"]
                })

        return jsonify({"user_id": user_id, "friends": friends_info}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching friends"}), 500

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
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Create transaction record
        transaction = {
            "_id": txn_id,
            "description": description,
            "amount": amount,
            "paid_by": paid_by,
            "split_among": split_among,
            "split_type": split_type,
            "split_details": split_details,
            "date":timestamp,
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
        splitwiseocollection = db.splitwise
        transactions_collection = splitwiseocollection.transactions
        users_collection = splitwiseocollection.users

        # Fetch transactions involving the user
        transactions = list(transactions_collection.find({
            "$or": [
                {"paid_by": user_id},
                {"split_among": {"$in": [user_id]}}
            ]
        }))

        # If no transactions are found, return an empty balances array
        if not transactions:
            return jsonify({
                "user_id": user_id,
                "balances": []  # Return an empty array
            }), 200

        # Calculate balances with friends
        balance_map = defaultdict(float)  # Store total balances as float values

        for txn in transactions:
            if txn["paid_by"] == user_id:
                # User paid for others, they are the lender
                for friend_id, amount in txn["split_details"].items():
                    if friend_id != user_id:  # Exclude self from balance calculations
                        balance_map[friend_id] += amount  # User lent money to friend

            elif user_id in txn["split_among"]:
                # User is part of the split, they owe the payer
                payer_id = txn["paid_by"]
                balance_map[payer_id] -= txn["split_details"][user_id]  # User owes money to payer

        # Fetch details of friends involved
        friend_ids = list(balance_map.keys())
        friends = list(users_collection.find({"_id": {"$in": friend_ids}}))
        friend_details = {
            str(friend["_id"]): {"name": friend["name"], "email": friend["email"]}
            for friend in friends
        }

        # Prepare response with the calculated relation (owe/lend) based on balance
        balances = []
        for friend_id, balance in balance_map.items():
            relation = "owe" if balance < 0 else "lend"  # Negative balance means owe, positive means lend
            balances.append({
                "friend_id": friend_id,
                "name": friend_details.get(friend_id, {}).get("name", "Unknown"),
                "email": friend_details.get(friend_id, {}).get("email", "Unknown"),
                "relation": relation,
                "amount": abs(balance)  # Absolute value of balance
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

        # Extract search query parameter
        search_query = request.args.get('q', '').strip()

        # Fetch collections
        splitwise_collection = db.splitwise
        user_collection = splitwise_collection.users

        # Get the current user's friends list
        current_user = user_collection.find_one({"_id": user_id}, {"friends": 1})
        if not current_user:
            return jsonify({"error": "Current user not found"}), 404

        friends = current_user.get("friends", [])

        # Build query filter
        query_filter = {"_id": {"$ne": user_id}}
        if search_query:
            # Add search condition for name or email
            query_filter["$or"] = [
                {"name": {"$regex": search_query, "$options": "i"}},
                {"email": {"$regex": search_query, "$options": "i"}}
            ]

        # Fetch users based on the filter
        users = user_collection.find(
            query_filter,
            {"_id": 1, "user_id": 1, "name": 1, "email": 1,"profile_pic":1}
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


def calculate_monthly_expense(transactions, user_id):
    monthly_expense = defaultdict(float)
    today = datetime.today()
    
    for txn in transactions:
        # Parse the date and extract the month key
        date = datetime.strptime(txn['date'], "%d %B")
        
        # Calculate the year: if the month is before the current month, subtract 1 from the year
        if date.month < today.month:
            year = today.year
        else:
            year = today.year - 1  # Adjust for December transactions
        
        # Combine the calculated year and the month to form the 'YYYY-MM' format
        month_key = f"{year}-{date.month:02d}"
        
        # Check if the user is part of the split
        if user_id in txn['split_among']:
            if txn['split_type'] == "equal":
                # Calculate equal split share
                share = txn['amount'] / len(txn['split_among'])
                if txn['paid_by'] != user_id:  # You owe someone
                    monthly_expense[month_key] += share
                else:  # You paid, add only your share
                    monthly_expense[month_key] += share

            elif txn['split_type'] == "exact":
                # Get exact share
                share = txn['split_details'].get(user_id, 0)
                if txn['paid_by'] != user_id:  # You owe someone
                    monthly_expense[month_key] += share
                else:  # You paid, add only your share
                    monthly_expense[month_key] += share

    return dict(monthly_expense)


# Filter transactions for the past four months and prepare the response
def get_expenses(user_id):
    today = datetime.today()
     
    four_months_ago = today - timedelta(days=120)  # Roughly 4 months window

    # Generate the list of past four months
    past_four_months = [
        (today - timedelta(days=30 * i)).strftime("%Y-%m")
        for i in range(4)
    ]
    
    # Query transactions from the database
    splitwiseocollection = db.splitwise
    transactions_collection = splitwiseocollection.transactions
    transactions = list(
        transactions_collection.find({
            "date": {"$gte": four_months_ago.strftime("%Y-%m-%d %H:%M:%S")},
            "split_among": {"$in": [user_id]}  # Filter only transactions where user is a participant
        })
    )
    

    # Process the filtered transactions
    monthly_expenses = calculate_monthly_expense(transactions, user_id)

    # Add zero for months with no expenses
    for month in past_four_months:
        if month not in monthly_expenses:
            monthly_expenses[month] = 0.0

    # Convert the response to user-friendly month names
    formatted_result = {
        datetime.strptime(month, "%Y-%m").strftime("%b"): monthly_expenses.get(month, 0.0)
        for month in past_four_months  # Ensure the output respects the order of the last four months
    }
  
    return formatted_result


# API endpoint
@app.route('/monthly_expense', methods=['POST'])
def monthly_expenses_api():
    try:
        # Fetch user ID from request payload
        data = request.json
        user_id = data.get('user_id')
        print(data)
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        # Compute the expenses
        expenses_summary = get_expenses(user_id)

        return jsonify({
            "message": "Expense computation successful",
            "data": expenses_summary
        }), 200

    except Exception as e:
        return jsonify({"error hello": str(e)}), 500



if __name__ == "__main__": 
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port, debug=True)

