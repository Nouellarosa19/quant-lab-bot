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

# 🔎 Verificar si usuario es premium
def get_user_premium(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_premium FROM users WHERE id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else False

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
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON inválido"}), 400

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
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "Usuario ya existe"}), 400
    except Exception:
        conn.rollback()
        return jsonify({"error": "Error en el servidor"}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "Usuario registrado correctamente"})

# 🔐 Login
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON inválido"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, password, is_admin FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and check_password_hash(user[1], password):
        session["user_id"] = user[0]
        session["is_admin"] = user[2]
        return jsonify({
            "message": "Login correcto",
            "is_admin": user[2]
        })

    return jsonify({"error": "Credenciales inválidas"}), 401

# 📊 Ruta Premium (solo usuarios premium o admin)
@app.route("/signals")
def signals():
    if not session.get("user_id"):
        return jsonify({"error": "Debes iniciar sesión"}), 401

    if not session.get("is_admin") and not get_user_premium(session.get("user_id")):
        return jsonify({"error": "Necesitas plan premium"}), 403

    return jsonify({"signal": "BTC LONG 🚀"})

# 👑 Panel Admin básico
@app.route("/admin")
def admin_panel():
    if not session.get("is_admin"):
        return jsonify({"error": "No autorizado"}), 403

    return jsonify({"message": "Bienvenido Admin"})

# 👥 Listar usuarios (solo admin)
@app.route("/admin/users")
def list_users():
    if not session.get("is_admin"):
        return jsonify({"error": "No autorizado"}), 403

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, is_admin, is_premium FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(users)

# 💎 Activar premium (solo admin)
@app.route("/make-premium/<int:user_id>", methods=["POST"])
def make_premium(user_id):
    if not session.get("is_admin"):
        return jsonify({"error": "No autorizado"}), 403

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_premium = TRUE WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": f"Usuario {user_id} ahora es premium"})

# 🚪 Logout
@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Sesión cerrada"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
