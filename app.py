from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import csv
import os
from datetime import datetime
import hashlib

app = Flask(__name__, static_folder="static")
CORS(app)

# ✅ CHECK API KEY
if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError("❌ OPENAI_API_KEY is not set")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ================================
# 🔥 SYSTEM PROMPT
# ================================
SYSTEM_PROMPT = """
You are a highly experienced obstetrics professor teaching medical students about preeclampsia using NICE and RCOG guidelines.

Your responsibilities:
1. Always interpret and correct spelling mistakes automatically.
2. Even if the user writes poorly, understand the intent.
3. Keep the topic strictly about preeclampsia.

Always respond in this clear structured format:

1. Definition
2. Causes / Pathophysiology
3. Signs and Symptoms
4. Diagnosis
5. Management

Then:
- End with ONE short question to test the student.

Rules:
- Be simple, clear, and educational
- Do NOT mention that you corrected spelling
- Do NOT go off-topic
- If input is unclear, assume it relates to preeclampsia and explain basics
"""

# ================================
# 🔐 HELPERS
# ================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_file_exists(filename):
    if not os.path.exists(filename):
        open(filename, "w").close()

# ================================
# 👤 USER FUNCTIONS
# ================================
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

# ================================
# 🌐 ROUTES
# ================================

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

# -------- REGISTER --------
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

# -------- LOGIN --------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid request"}), 400

    if check_user(data.get("username"), data.get("password")):
        return jsonify({"status": "success"})

    return jsonify({"status": "fail"})

# -------- CHAT --------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid request"}), 400

    student_input = data.get("message", "")
    username = data.get("username", "anonymous")

    cleaned_input = student_input.strip().lower()

    try:
        # ✅ FIXED API CALL
        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"""
The student wrote the following (may contain spelling mistakes):
\"{cleaned_input}\"

Interpret the meaning and respond accordingly about preeclampsia.
"""}
            ],
            temperature=0.5
        )

        reply = response.output_text

        # 💾 SAVE DATA
        ensure_file_exists("data.csv")
        with open("data.csv", "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.now(),
                username,
                student_input,
                reply
            ])

        return jsonify({"reply": reply})

    except Exception as e:
        print("🔥 ERROR:", e)
        return jsonify({"error": "Server crashed. Check backend logs."}), 500

# ================================
# 🚀 RUN SERVER
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
