import os
import psycopg2
import uuid
from flask import Flask, request, render_template_string, redirect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

# =============================
# CREAR TABLAS
# =============================

def crear_tablas():
    conn = get_db()
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

    conn.commit()
    cur.close()
    conn.close()

crear_tablas()

# =============================
# REGISTRO
# =============================

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed = generate_password_hash(password)

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO usuarios (username, password, rol) VALUES (%s,%s,%s)",
                (username, hashed, "user")
            )
            conn.commit()
        except:
            return "Usuario ya existe"

        cur.close()
        conn.close()

        return redirect("/")

    return render_template_string("""
        <h2>Registro</h2>
        <form method="POST">
            Usuario:<br>
            <input name="username"><br>
            Password:<br>
            <input type="password" name="password"><br><br>
            <button type="submit">Crear cuenta</button>
        </form>
    """)

# =============================
# LOGIN
# =============================

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT password, rol FROM usuarios WHERE username=%s", (username,))
        user = cur.fetchone()

        if user and check_password_hash(user[0], password):
            token = str(uuid.uuid4())
            cur.execute("UPDATE usuarios SET token=%s WHERE username=%s", (token, username))
            conn.commit()
            cur.close()
            conn.close()

            if user[1] == "admin":
                return redirect(f"/admin?token={token}")
            else:
                return redirect(f"/dashboard?token={token}")

        return "Credenciales inválidas"

    return render_template_string("""
        <h2>Login</h2>
        <form method="POST">
            Usuario:<br>
            <input name="username"><br>
            Password:<br>
            <input type="password" name="password"><br><br>
            <button type="submit">Entrar</button>
        </form>
        <br>
        <a href="/register">Crear cuenta</a>
    """)

# =============================
# DASHBOARD USER
# =============================

@app.route("/dashboard")
def dashboard():
    token = request.args.get("token")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username FROM usuarios WHERE token=%s", (token,))
    user = cur.fetchone()

    if not user:
        return "No autorizado"

    return f"""
        <h2>Dashboard Usuario</h2>
        <p>Bienvenido {user[0]}</p>
        <p>Sistema estable ✅</p>
    """

# =============================
# DASHBOARD ADMIN
# =============================

@app.route("/admin")
def admin():
    token = request.args.get("token")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, rol FROM usuarios WHERE token=%s", (token,))
    user = cur.fetchone()

    if not user or user[1] != "admin":
        return "No autorizado"

    cur.execute("SELECT id, username, rol FROM usuarios")
    users = cur.fetchall()

    return f"""
        <h2>Admin Panel</h2>
        <pre>{users}</pre>
    """

# =============================
# RUN LOCAL
# =============================

if __name__ == "__main__":
    app.run()
