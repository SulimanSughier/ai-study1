from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import csv
import os
from datetime import datetime
import hashlib

app = Flask(__name__, static_folder="static")
CORS(app)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert obstetrics tutor teaching medical students about preeclampsia using NICE and RCOG guidelines.

Provide a clear, detailed explanation, then ask one question.
"""

# ---------- HELPERS ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_file_exists(filename):
    if not os.path.exists(filename):
        open(filename, "w").close()

# ---------- USER ----------
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
        return any(row and row[0] == username and row[1] == hash_password(password)
                   for row in csv.reader(f))

# ---------- ROUTES ----------
@app.route("/")
def serve_ui():
    return send_from_directory("static", "index.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid request"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing fields"}), 400

    if user_exists(username):
        return jsonify({"status": "exists"})

    add_user(username, password)
    return jsonify({"status": "created"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid request"}), 400

    if check_user(data.get("username"), data.get("password")):
        return jsonify({"status": "success"})

    return jsonify({"status": "fail"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid request"}), 400

    student_input = data.get("message")
    username = data.get("username", "anonymous")

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": student_input}
            ]
        )

        reply = response.choices[0].message.content

        # Save conversation
        ensure_file_exists("data.csv")
        with open("data.csv", "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now(), username, student_input, reply])

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
