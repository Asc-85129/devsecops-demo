"""
Fixed version of the demo app. Swap it in live with:  cp app.fixed.py app.py
Changes vs app.py: parameterised SQL query (CWE-89 fixed), input length check,
basic security headers (picked up by the ZAP baseline scan), and the bind
address comes from $HOST instead of a hard-coded 0.0.0.0.
"""
from flask import Flask, request
import sqlite3
import os
import tempfile

app = Flask(__name__)
# Writable location for the SQLite file (the image filesystem may be read-only or owned by root)
DB_PATH = os.environ.get("DB_PATH", os.path.join(tempfile.gettempdir(), "demo.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, role TEXT)")
    conn.execute("INSERT INTO users (username, role) SELECT 'admin', 'admin' WHERE NOT EXISTS (SELECT 1 FROM users)")
    conn.commit()
    return conn


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response


@app.route("/")
def home():
    return "DevSecOps demo app is running. Try /user?name=admin"


# FIXED: user input is passed as a bound parameter, never concatenated into SQL
@app.route("/user")
def get_user():
    name = request.args.get("name", "")
    if len(name) > 64:
        return {"error": "name too long"}, 400
    conn = get_db()
    cursor = conn.execute("SELECT id, username, role FROM users WHERE username = ?", (name,))
    rows = cursor.fetchall()
    conn.close()
    return {"results": rows}


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # FIXED: localhost by default; the container image opts in to 0.0.0.0 via HOST
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
