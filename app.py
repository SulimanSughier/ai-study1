from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import csv
import os
from datetime import datetime
import hashlib

app = Flask(__name__, static_folder="static")
CORS(app)

# ✅ API KEY CHECK
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is not set")

client = OpenAI(api_key=API_KEY)

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
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_file_exists(filename):
    if not os.path.exists(filename):
        open(filename, "w").close()

# ================================
# USER SYSTEM
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
# ROUTES
# ================================

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

# -------- REGISTER --------
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Missing fields"}), 400

        if user_exists(username):
            return jsonify({"status": "exists"})

        add_user(username, password)
        return jsonify({"status": "created"})

    except Exception as e:
        print("REGISTER ERROR:", e)
        return jsonify({"error": "Server error"}), 500

# -------- LOGIN --------
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        if check_user(data.get("username"), data.get("password")):
            return jsonify({"status": "success"})

        return jsonify({"status": "fail"})

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"error": "Server error"}), 500

# -------- CHAT --------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        student_input = data.get("message", "")
        username = data.get("username", "anonymous")

        print("User:", username, "| Message:", student_input)

        # ✅ SAFE API CALL
        response = client.responses.create(
            model="gpt-4o-mini",  # ✅ stable & cheap
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": student_input}
            ]
        )

        # ✅ SAFE RESPONSE EXTRACTION
        reply = ""
        try:
            reply = response.output_text
        except:
            try:
                reply = response.output[0].content[0].text
            except:
                reply = "⚠️ AI returned no response"

        # 💾 SAVE CHAT
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
        print("🔥 CHAT ERROR:", e)
        return jsonify({"error": str(e)}), 500

# ================================
# RUN
# ================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
