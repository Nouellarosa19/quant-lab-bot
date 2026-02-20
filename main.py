import os
import psycopg2
from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# 🔐 Secret Key
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# 🔗 Conexión DB
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

# 🏗️ Crear tablas automáticamente
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            is_premium BOOLEAN DEFAULT FALSE
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

# 👑 Crear admin automático
def create_admin():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = %s", ("admin@quantlab.com",))
    admin = cur.fetchone()

    if not admin:
        hashed_password = generate_password_hash("admin123")
        cur.execute(
            "INSERT INTO users (email, password, is_admin, is_premium) VALUES (%s, %s, %s, %s)",
            ("admin@quantlab.com", hashed_password, True, True)
        )
        conn.commit()

    cur.close()
    conn.close()

# 🚀 Ejecutar al iniciar
create_tables()
create_admin()

# 🌍 Ruta raíz
@app.route("/")
def home():
    return "API funcionando 🚀"

# 📝 Registro
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        hashed_password = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email, hashed_password)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Usuario ya existe"}), 400
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "Usuario registrado correctamente"})

# 🔐 Login
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, password, is_admin FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and check_password_hash(user[1], password):
        session["user_id"] = user[0]
        session["is_admin"] = user[2]
        return jsonify({"message": "Login correcto"})
    
    return jsonify({"error": "Credenciales inválidas"}), 401

# 👑 Panel Admin
@app.route("/admin")
def admin_panel():
    if not session.get("is_admin"):
        return jsonify({"error": "No autorizado"}), 403

    return jsonify({"message": "Bienvenido Admin"})

# 🚪 Logout
@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Sesión cerrada"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
