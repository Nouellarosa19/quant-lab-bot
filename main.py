import os
import time
import threading
import psycopg2
from flask import Flask

app = Flask(__name__)

# ==========================
# CONEXIÓN A POSTGRES (Railway)
# ==========================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL no está definida")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

print("✅ Base de datos conectada correctamente")

# ==========================
# CREAR TABLA SI NO EXISTE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS bot_config (
    id SERIAL PRIMARY KEY,
    riesgo FLOAT,
    agresividad FLOAT
);
""")

print("✅ Tabla verificada")

# ==========================
# RUTA WEB (Railway necesita esto)
# ==========================

@app.route("/")
def home():
    return "Bot activo, base de datos conectada y funcionando"

# ==========================
# LOOP DEL BOT
# ==========================

def bot_loop():
    while True:
        print("🤖 Bot funcionando...")
        time.sleep(60)

# ==========================
# INICIO DEL SERVIDOR
# ==========================

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
