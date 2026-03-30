from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import csv
import os
from datetime import datetime
import hashlib

app = Flask(__name__)
CORS(app)

# ✅ FIX: use environment variable for API key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert obstetrics tutor teaching medical students about preeclampsia using NICE and RCOG guidelines.

Provide a clear, detailed explanation, then ask one question.
"""

# -------- PASSWORD HASH --------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------- USER FUNCTIONS --------
def user_exists(username):
    if not os.path.exists("users.csv"):
        return False
    with open("users.csv", "r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row[0] == username:
                return True
    return False

def add_user(username, password):
    with open("users.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([username, hash_password(password)])

def check_user(username, password):
    if not os.path.exists("users.csv"):
        return False
    with open("users.csv", "r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row[0] == username and row[1] == hash_password(password):
                return True
    return False

# -------- TEST ROUTE (IMPORTANT FOR PHONE) --------
@app.route("/")
def home():
    return "Server is running ✅"

# -------- REGISTER --------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if user_exists(username):
        return jsonify({"status": "exists"})

    add_user(username, password)
    return jsonify({"status": "created"})

# -------- LOGIN --------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if check_user(data.get("username"), data.get("password")):
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

# -------- CHAT --------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    student_input = data.get("message")
    username = data.get("username")

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": student_input}
        ]
    )

    reply = response.choices[0].message.content

    # SAVE DATA
    with open("data.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), username, student_input, reply])

    return jsonify({"reply": reply})

# ✅ CRITICAL FIX FOR MOBILE + DEPLOYMENT
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
