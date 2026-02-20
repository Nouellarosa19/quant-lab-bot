import os
import time
import threading
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot activo y funcionando"

def bot_loop():
    while True:
        print("Bot funcionando...")
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
