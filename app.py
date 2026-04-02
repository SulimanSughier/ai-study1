from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import csv
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

client = OpenAI()

SYSTEM_PROMPT = """You are an expert obstetrics tutor teaching medical students about preeclampsia using NICE and RCOG guidelines.

Provide a clear, detailed explanation, then ask one question.
"""

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
        writer.writerow([username, password])

def check_user(username, password):
    if not os.path.exists("users.csv"):
        return False
    with open("users.csv", "r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row[0] == username and row[1] == password:
                return True
    return False

# -------- REGISTER --------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data["username"]
    password = data["password"]

    if user_exists(username):
        return jsonify({"status": "exists"})

    add_user(username, password)
    return jsonify({"status": "created"})

# -------- LOGIN --------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if check_user(data["username"], data["password"]):
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

# -------- CHAT + SAVE DATA --------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    student_input = data["message"]
    username = data["username"]

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": student_input}
        ]
    )

    reply = response.choices[0].message.content

    # SAVE DATA (UTF-8 FIXED)
    with open("data.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), username, student_input, reply])

    return jsonify({
        "reply": reply
    })

app.run(debug=True)
