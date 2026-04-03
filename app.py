from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import csv
import hashlib
import logging
from datetime import datetime
from openai import OpenAI

# ================================
# LOGGING
# ================================
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")

# ================================
# CORS
# ================================
CORS(app, origins=[
    "https://sulimansughier.github.io",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
])

# ================================
# API KEY
# ================================
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")

client = OpenAI(api_key=API_KEY)

# ================================
# FILE PATHS
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.csv")
DATA_FILE  = os.path.join(BASE_DIR, "data.csv")

# ================================
# SYSTEM PROMPT
# ================================
SYSTEM_PROMPT = """
You are a medical tutor teaching preeclampsia.

Always answer in this format:
1. Definition
2. Causes
3. Symptoms
4. Diagnosis
5. Management

End with one short question.
Keep it simple.
"""

# ================================
# HELPERS
# ================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_file_exists(filepath: str) -> None:
    dir_name = os.path.dirname(filepath)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    if not os.path.exists(filepath):
        with open(filepath, "w", newline="", encoding="utf-8"):
            pass

# ================================
# USER SYSTEM
# ================================
def user_exists(username: str) -> bool:
    ensure_file_exists(USERS_FILE)
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if row and len(row) >= 4 and row[1].strip() == username:
                    return True
    except Exception as e:
        logger.error("user_exists ERROR: %s", e)
    return False

def add_user(username: str, password: str) -> None:
    ensure_file_exists(USERS_FILE)
    try:
        with open(USERS_FILE, "a", newline="", encoding="utf-8") as f:
            timestamp = datetime.now().isoformat()
            hashed = hash_password(password)

            # timestamp, username, plain_password, hashed_password
            csv.writer(f).writerow([timestamp, username, password, hashed])
    except Exception as e:
        logger.error("add_user ERROR: %s", e)
        raise

def check_user(username: str, password: str) -> bool:
    ensure_file_exists(USERS_FILE)
    hashed = hash_password(password)
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if row and len(row) >= 4:
                    saved_username = row[1].strip()
                    saved_hashed = row[3]

                    if saved_username == username and saved_hashed == hashed:
                        return True
    except Exception as e:
        logger.error("check_user ERROR: %s", e)
    return False

# ================================
# ROUTES
# ================================
@app.route("/")
def home():
    return send_from_directory("static", "index.html")

# -------- REGISTER --------
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid request format"}), 400

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        if user_exists(username):
            return jsonify({"error": "User already exists"}), 409

        add_user(username, password)
        logger.info("New user registered: %s", username)
        return jsonify({"status": "success", "message": "Registration successful"}), 201

    except Exception as e:
        logger.error("REGISTER ERROR: %s", e)
        return jsonify({"error": "Server error", "detail": str(e)}), 500

# -------- LOGIN --------
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid request format"}), 400

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        if check_user(username, password):
            logger.info("User logged in: %s", username)

            # Save login activity
            ensure_file_exists(DATA_FILE)
            with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    datetime.now().isoformat(),
                    username,
                    password,
                    "LOGIN"
                ])

            return jsonify({"status": "success"}), 200

        return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        logger.error("LOGIN ERROR: %s", e)
        return jsonify({"error": "Server error", "detail": str(e)}), 500

# -------- CHAT --------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid request format"}), 400

        student_input = data.get("message", "").strip()
        username = data.get("username", "anonymous")

        if not student_input:
            return jsonify({"error": "Empty message"}), 400

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": student_input}
            ]
        )

        reply = response.choices[0].message.content

        ensure_file_exists(DATA_FILE)
        with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.now().isoformat(),
                username,
                student_input,
                reply
            ])

        return jsonify({"reply": reply}), 200

    except Exception as e:
        logger.error("CHAT ERROR: %s", e)
        return jsonify({"error": "Server error", "detail": str(e)}), 500

# ================================
# RUN
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
