import os
import sqlite3
from functools import wraps

import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "translator.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "replace-this-with-a-long-random-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

# MyMemory provides a free translation endpoint. Free usage is rate-limited.
TRANSLATION_API = "https://api.mymemory.translated.net/get"

LANGUAGES = {
    "ar": "Arabic", "bn": "Bengali", "zh-CN": "Chinese (Simplified)",
    "nl": "Dutch", "en": "English", "fr": "French", "de": "German",
    "el": "Greek", "gu": "Gujarati", "hi": "Hindi", "id": "Indonesian",
    "it": "Italian", "ja": "Japanese", "kn": "Kannada", "ko": "Korean",
    "ml": "Malayalam", "mr": "Marathi", "ne": "Nepali", "pt": "Portuguese",
    "pa": "Punjabi", "ru": "Russian", "es": "Spanish", "ta": "Tamil",
    "te": "Telugu", "th": "Thai", "tr": "Turkish", "ur": "Urdu",
    "vi": "Vietnamese"
}

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source_language TEXT NOT NULL,
                target_language TEXT NOT NULL,
                original_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("translator"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("Please fill in all fields.", "error")
        elif len(username) < 3:
            flash("Username must contain at least 3 characters.", "error")
        elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            flash("Enter a valid email address.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                        (username, email, generate_password_hash(password))
                    )
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username or email is already registered.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (identity, identity.lower())
            ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("translator"))
        flash("Invalid username/email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/translator", methods=["GET"])
@login_required
def translator():
    with get_db() as conn:
        history = conn.execute(
            """SELECT source_language, target_language, original_text,
                      translated_text, created_at
               FROM translations WHERE user_id = ?
               ORDER BY id DESC LIMIT 8""",
            (session["user_id"],)
        ).fetchall()
    return render_template(
        "translator.html",
        languages=LANGUAGES,
        history=history,
        username=session.get("username")
    )

@app.route("/translate", methods=["POST"])
@login_required
def translate():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    source = data.get("source") or "en"
    target = data.get("target") or "hi"

    if not text:
        return jsonify(success=False, error="Enter some text to translate."), 400
    if len(text) > 5000:
        return jsonify(success=False, error="Please limit the input to 5,000 characters."), 400
    if source not in LANGUAGES or target not in LANGUAGES:
        return jsonify(success=False, error="Please select valid languages."), 400
    if source == target:
        return jsonify(success=False, error="Choose two different languages."), 400

    try:
        response = requests.get(
            TRANSLATION_API,
            params={"q": text, "langpair": f"{source}|{target}"},
            timeout=20,
            headers={"User-Agent": "LanguageTranslationTool/1.0"}
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("responseStatus") != 200:
            message = payload.get("responseDetails") or "The translation service could not process this request."
            return jsonify(success=False, error=message), 502

        translated = payload.get("responseData", {}).get("translatedText", "")
        if not translated:
            return jsonify(success=False, error="No translated text was returned. Please try again."), 502

        with get_db() as conn:
            conn.execute(
                """INSERT INTO translations
                   (user_id, source_language, target_language, original_text, translated_text)
                   VALUES (?, ?, ?, ?, ?)""",
                (session["user_id"], source, target, text, translated)
            )
        return jsonify(success=True, translated_text=translated)
    except requests.Timeout:
        return jsonify(success=False, error="Translation service timed out. Please try again."), 504
    except requests.RequestException:
        return jsonify(success=False, error="Could not connect to the translation service. Check your internet connection."), 502
    except (ValueError, KeyError):
        return jsonify(success=False, error="Received an unexpected response from the translation service."), 502

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
