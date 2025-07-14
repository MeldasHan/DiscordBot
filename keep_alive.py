from flask import Flask
from threading import Thread
import logging

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive"

def run():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # ✅ 抑制 Flask 輸出
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True  # ✅ 確保主線程結束時會自動結束
    t.start()
