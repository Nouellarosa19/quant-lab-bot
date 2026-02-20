import os
import psycopg2
import requests
import hmac
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, redirect, session, jsonify

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

# ==============================
# DATABASE
# ==============================

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def crear_tablas():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            password TEXT,
            token TEXT,
            plan VARCHAR(20),
            activo BOOLEAN DEFAULT FALSE,
            expira TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

crear_tablas()

# ==============================
# REGISTRO
# ==============================

@app.route("/register", methods=["POST"])
def register():
    username = request.json.get("username")
    password = request.json.get("password")
    token = os.urandom(16).hex()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios (username, password, token, plan, activo) VALUES (%s,%s,%s,%s,%s)",
        (username, password, token, "free", False)
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Usuario creado", "token": token})

# ==============================
# LOGIN
# ==============================

@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username")
    password = request.json.get("password")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT token FROM usuarios WHERE username=%s AND password=%s",
        (username, password)
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user:
        return jsonify({"token": user[0]})
    else:
        return jsonify({"error": "Credenciales inválidas"}), 401

# ==============================
# CREAR FACTURA (10 USDT)
# ==============================

@app.route("/buy-premium")
def buy_premium():
    token = request.args.get("token")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username FROM usuarios WHERE token=%s", (token,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return "No autorizado"

    api_key = os.getenv("NOWPAYMENTS_API_KEY")

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "price_amount": 10,
        "price_currency": "usd",
        "pay_currency": "usdt",
        "order_id": user[0],
        "order_description": "Premium 30 dias"
    }

    response = requests.post(
        "https://api.nowpayments.io/v1/invoice",
        json=payload,
        headers=headers
    )

    data = response.json()

    if "invoice_url" in data:
        return redirect(data["invoice_url"])
    else:
        return str(data)

# ==============================
# WEBHOOK SEGURO
# ==============================

@app.route("/webhook", methods=["POST"])
def webhook():
    ipn_secret = os.getenv("NOWPAYMENTS_IPN_SECRET")
    received_hmac = request.headers.get("x-nowpayments-sig")

    raw_body = request.get_data()

    calculated_hmac = hmac.new(
        ipn_secret.encode(),
        raw_body,
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(calculated_hmac, received_hmac):
        return "Firma inválida", 400

    data = request.json

    if data.get("payment_status") == "finished":
        username = data.get("order_id")

        conn = get_db()
        cur = conn.cursor()

        expiration = datetime.utcnow() + timedelta(days=30)

        cur.execute("""
            UPDATE usuarios 
            SET plan=%s, activo=%s, expira=%s 
            WHERE username=%s
        """, ("premium", True, expiration, username))

        conn.commit()
        cur.close()
        conn.close()

    return "OK"

# ==============================
# RUTA PREMIUM PROTEGIDA
# ==============================

@app.route("/premium")
def premium():
    token = request.args.get("token")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT activo, expira FROM usuarios WHERE token=%s
    """, (token,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return "No autorizado"

    activo, expira = user

    if activo and expira and expira > datetime.utcnow():
        return "Bienvenido a contenido PREMIUM 🔥"
    else:
        return "Tu plan no está activo o expiró"

# ==============================
# HOME
# ==============================

@app.route("/")
def home():
    return "API funcionando 🚀"

# ==============================
# RAILWAY PORT DINÁMICO
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
