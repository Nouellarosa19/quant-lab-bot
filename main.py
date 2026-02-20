import os
import psycopg2
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# =====================================
# CONEXIÓN A BASE DE DATOS
# =====================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL no está definida")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# =====================================
# CREAR TABLAS
# =====================================

def crear_tablas():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            password TEXT,
            rol VARCHAR(20),
            token TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuraciones (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(100),
            estrategia VARCHAR(100),
            moneda VARCHAR(20),
            riesgo FLOAT,
            agresividad FLOAT,
            capital FLOAT,
            fecha_actualizacion TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

crear_tablas()


# =====================================
# RUTA PRINCIPAL
# =====================================

@app.route("/")
def home():
    return "Bot activo, base de datos conectada y funcionando"


# =====================================
# REGISTRO
# =====================================

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Faltan datos"}), 400

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO usuarios (username, password, rol)
            VALUES (%s, %s, %s)
        """, (username, hashed_password, "user"))
        conn.commit()
    except:
        return jsonify({"error": "Usuario ya existe"}), 400

    cur.close()
    conn.close()

    return jsonify({"mensaje": "Usuario creado correctamente"})


# =====================================
# LOGIN
# =====================================

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT password FROM usuarios WHERE username=%s", (username,))
    user = cur.fetchone()

    if user and check_password_hash(user[0], password):
        token = str(uuid.uuid4())
        cur.execute("UPDATE usuarios SET token=%s WHERE username=%s", (token, username))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"token": token})

    cur.close()
    conn.close()
    return jsonify({"error": "Credenciales inválidas"}), 401


# =====================================
# VERIFICAR TOKEN
# =====================================

def verificar_token(token):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, rol FROM usuarios WHERE token=%s", (token,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


# =====================================
# GUARDAR CONFIG (USER o ADMIN)
# =====================================

@app.route("/config", methods=["POST"])
def guardar_config():

    token = request.headers.get("Authorization")
    user = verificar_token(token)

    if not user:
        return jsonify({"error": "No autorizado"}), 401

    username_logueado, rol = user
    data = request.json

    # Si es admin puede modificar otro usuario
    usuario_objetivo = data.get("usuario") if rol == "admin" else username_logueado

    estrategia = data.get("estrategia")
    moneda = data.get("moneda")
    riesgo = data.get("riesgo")
    agresividad = data.get("agresividad")
    capital = data.get("capital")

    if not estrategia or not moneda:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM configuraciones
        WHERE usuario=%s AND estrategia=%s AND moneda=%s
    """, (usuario_objetivo, estrategia, moneda))

    existe = cur.fetchone()

    if existe:
        cur.execute("""
            UPDATE configuraciones
            SET riesgo=%s, agresividad=%s, capital=%s, fecha_actualizacion=%s
            WHERE usuario=%s AND estrategia=%s AND moneda=%s
        """, (riesgo, agresividad, capital, datetime.now(),
              usuario_objetivo, estrategia, moneda))
    else:
        cur.execute("""
            INSERT INTO configuraciones
            (usuario, estrategia, moneda, riesgo, agresividad, capital, fecha_actualizacion)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (usuario_objetivo, estrategia, moneda, riesgo,
              agresividad, capital, datetime.now()))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"mensaje": "Configuración guardada"})


# =====================================
# VER CONFIG PROPIA
# =====================================

@app.route("/my-configs", methods=["GET"])
def mis_configs():

    token = request.headers.get("Authorization")
    user = verificar_token(token)

    if not user:
        return jsonify({"error": "No autorizado"}), 401

    username, rol = user

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT usuario, estrategia, moneda, riesgo, agresividad, capital, fecha_actualizacion
        FROM configuraciones
        WHERE usuario=%s
    """, (username,))

    datos = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(datos)


# =====================================
# ADMIN - VER TODOS LOS USUARIOS
# =====================================

@app.route("/admin/users", methods=["GET"])
def admin_ver_usuarios():

    token = request.headers.get("Authorization")
    user = verificar_token(token)

    if not user or user[1] != "admin":
        return jsonify({"error": "Solo admin"}), 403

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username, rol FROM usuarios")
    usuarios = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(usuarios)


# =====================================
# ADMIN - VER TODAS LAS CONFIGURACIONES
# =====================================

@app.route("/admin/configs", methods=["GET"])
def admin_ver_configs():

    token = request.headers.get("Authorization")
    user = verificar_token(token)

    if not user or user[1] != "admin":
        return jsonify({"error": "Solo admin"}), 403

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT usuario, estrategia, moneda, riesgo, agresividad, capital, fecha_actualizacion
        FROM configuraciones
    """)

    configs = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(configs)


# =====================================
# RUN
# =====================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
