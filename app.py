from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import csv
import hashlib
from datetime import datetime
from openai import OpenAI

app = Flask(__name__, static_folder="static")
CORS(app)

# API Key Check
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")

client = OpenAI(api_key=API_KEY)

# System Prompt
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

# Helpers
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_file_exists(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            pass

# User System
def user_exists(username):
    ensure_file_exists("users.csv")
    with open("users.csv", "r", encoding="utf-8") as f:
        return any(row and row[0] == username for row in csv.reader(f))

def add_user(username, password):
    with open("users.csv", "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([username, hash_password(password)])

def check_user(username, password):
    ensure_file_exists("users.csv")
    with open("users.csv", "r", encoding="utf-8") as f:
        return any(
            row and row[0] == username and row[1] == hash_password(password)
            for row in csv.reader(f)
        )

# Routes
@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "Missing fields"}), 400

    if user_exists(username):
        return jsonify({"error": "User already exists"}), 400

    add_user(username, password)
    return jsonify({"status": "User created successfully"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    
    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "Missing fields"}), 400

    if check_user(data["username"], data["password"]):
        return jsonify({"status": "Login successful"}), 200

    return jsonify({"error": "Invalid username or password"}), 401

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    student_input = data.get("message", "")
    username = data.get("username", "anonymous")

    if not student_input:
        return jsonify({"error": "Empty message"}), 400

    # Safe API Call
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": student_input}
            ]
        )

        reply = response.output_text or "⚠️ AI returned no response"

    except Exception as e:
        print("Chat API error:", e)
        return jsonify({"error": "Could not get a response from AI"}), 500

    # Save Chat
    ensure_file_exists("data.csv")
    with open("data.csv", "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.now(),
            username,
            student_input,
            reply
        ])

    return jsonify({"reply": reply}), 200

# Run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
