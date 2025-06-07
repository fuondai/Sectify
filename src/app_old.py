# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, session, redirect, request, jsonify # Added jsonify
from functools import wraps
import pymongo
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv # To load environment variables from .env file

# Load environment variables from .env file if it exists
load_dotenv()

app = Flask(__name__)

# --- Load Configuration Securely ---
# Load Flask secret key from environment variable
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY environment variable not set. Please set a strong secret key.")
    # In production, you might want to generate one if not set, but for development, raising an error is better.
    # For example: app.secret_key = os.urandom(24)

# Load MongoDB connection string from environment variable
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set. Please provide the MongoDB connection string.")

# Load JWT expiration time (in minutes) from environment variable, default to 15 minutes
app.config["JWT_EXPIRATION_MINUTES"] = int(os.environ.get("JWT_EXPIRATION_MINUTES", 15))

# Configure session lifetime (optional, Flask sessions have their own lifetime)
app.permanent_session_lifetime = timedelta(minutes=int(os.environ.get("SESSION_LIFETIME_MINUTES", 30)))

# --- Database Connection ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    # The ismaster command is cheap and does not require auth.
    client.admin.command("ismaster") 
    db = client.get_database() # Get default database from URI or specify one: client["MMH"]
    print("Connected successfully to MongoDB!")
except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    # Handle connection error appropriately (e.g., exit, retry, log)
    db = None # Indicate DB is not available
except Exception as e:
    print(f"An error occurred during MongoDB connection: {e}")
    db = None

# --- Authentication Decorators ---
def token_required(func):
    """Decorator to verify JWT token in session."""
    @wraps(func)
    def decorated(*args, **kwargs):
        token = session.get("token")
        if not token:
            print("Token required: No token found in session.")
            # Consider returning a JSON error for API endpoints
            if request.endpoint and (request.endpoint.startswith("api_") or "api" in request.endpoint):
                 return jsonify({"error": "Authentication token required"}), 401
            return redirect("/login/")
        try:
            # Decode the token using the app's secret key
            payload = jwt.decode(token, app.secret_key, algorithms=["HS256"])
            # Store payload in session or request context if needed downstream
            session["user_id"] = payload.get("id") 
            print(f"Token verified successfully for user_id: {session['user_id']}")
        except jwt.ExpiredSignatureError:
            print("Token required: Token has expired.")
            session.clear() # Clear session on expired token
            if request.endpoint and (request.endpoint.startswith("api_") or "api" in request.endpoint):
                 return jsonify({"error": "Token has expired"}), 401
            return redirect("/login/")
        except jwt.InvalidTokenError as e:
            print(f"Token required: Invalid token. Error: {e}")
            session.clear() # Clear session on invalid token
            if request.endpoint and (request.endpoint.startswith("api_") or "api" in request.endpoint):
                 return jsonify({"error": "Invalid token"}), 401
            return redirect("/login/")
        except Exception as e:
            print(f"Token required: An unexpected error occurred during token decoding: {e}")
            session.clear()
            if request.endpoint and (request.endpoint.startswith("api_") or "api" in request.endpoint):
                 return jsonify({"error": "Authentication error"}), 500
            return redirect("/login/")
            
        return func(*args, **kwargs)
    return decorated

def login_required(f):
    """Decorator to check if user is logged in via session variable."""
    @wraps(f)
    def wrap(*args, **kwargs):
        # Check for a more reliable session variable like 'user_id' set by token_required
        if "logged_in" in session and session["logged_in"] and "user_id" in session:
            return f(*args, **kwargs)
        else:
            print("Login required: User not logged in.")
            session.clear()
            if request.endpoint and (request.endpoint.startswith("api_") or "api" in request.endpoint):
                 return jsonify({"error": "Login required"}), 401
            return redirect("/login/") # Redirect to login page
    return wrap

# --- Routes ---
# Import routes after app and db initialization
# Ensure routes files also import the configured 'db' instance from this app.py
from routes import audio_route, user_routes 

@app.route("/")
def home():
    # Check if user is already logged in, redirect to dashboard if so
    if "logged_in" in session and session["logged_in"]:
        return redirect("/dashboard/")
    return render_template("home.html")

@app.route("/login/")
def loginn():
     # Check if user is already logged in, redirect to dashboard if so
    if "logged_in" in session and session["logged_in"]:
        return redirect("/dashboard/")
    return render_template("login.html")

@app.route("/signup/")
def signupp():
     # Check if user is already logged in, redirect to dashboard if so
    if "logged_in" in session and session["logged_in"]:
        return redirect("/dashboard/")
    # Assuming signup form is on home.html or create a dedicated signup.html
    return render_template("home.html") # Or redirect to a dedicated signup page

@app.route("/dashboard/")
@login_required # Ensures basic session login
@token_required # Ensures valid JWT token
def dashboard():
    # user_info = session.get("user") # Get user info if stored in session
    # Pass necessary user info to the template
    user_id = session.get("user_id")
    # Fetch user details from DB if needed, avoid storing too much in session
    user_details = db.users.find_one({"_id": user_id}, {"password": 0}) # Exclude password
    return render_template("user-info.html", user=user_details)

@app.route("/audioplay/")
@login_required
@token_required
def audio():
    # Add logic to fetch and list available audio files for the user
    return render_template("audio-play.html")

@app.route("/sendaudio/")
@login_required
@token_required
def sendaudio():
    role = session.get("role")
    if role == "admin":
        print(f"Admin user accessing sendaudio page.")
        return render_template("upload.html")
    else:
        print(f"Regular user accessing sendaudio page (redirected to user view).")
        # Maybe redirect non-admins or show a different view
        # return render_template("user.html") # Original logic
        return redirect("/dashboard/") # Example: Redirect non-admins to dashboard

# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404 # Create a 404.html template

@app.errorhandler(500)
def internal_server_error(e):
    print(f"Internal Server Error: {e}") # Log the error
    return render_template("500.html"), 500 # Create a 500.html template

# --- Main Execution Guard ---
if __name__ == "__main__":
    if not db:
        print("Database connection failed. Exiting.")
        exit(1)
    # Run the Flask app
    # Use environment variables for host and port, default to 0.0.0.0:5000
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_RUN_PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    print(f"Starting Flask app on {host}:{port} with debug mode: {debug_mode}")
    app.run(host=host, port=port, debug=debug_mode)

