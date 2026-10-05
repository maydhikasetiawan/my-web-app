import os
import psycopg2
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Mengambil konfigurasi database dari Environment Variables
DB_HOST = os.getenv('DB_HOST', 'postgres-server')
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
LOG_FILE_PATH = '/var/log/nginx/access.log'

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=5432
    )

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Membuat tabel jika belum ada
        cur.execute('''
            CREATE TABLE IF NOT EXISTS nginx_logs (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45),
                timestamp VARCHAR(100),
                method VARCHAR(10),
                endpoint TEXT,
                status_code INT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error initializing DB: {e}")

# Jalankan inisialisasi tabel saat aplikasi start
init_db()

def parse_and_sync_logs():
    if not os.path.exists(LOG_FILE_PATH):
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        with open(LOG_FILE_PATH, 'r') as f:
            lines = f.readlines()[-200:]  # Ambil 200 baris log Nginx terakhir

            for line in lines:
                parts = line.split(' ')
                if len(parts) >= 7:
                    ip = parts[0]

                    # Abaikan log internal / healthcheck
                    if ip in ['127.0.0.1', '::1'] or ip.startswith('172.'):
                        continue

                    try:
                        timestamp = line[line.find("[")+1:line.find("]")]
                        request_part = line[line.find('"')+1:]
                        req_subparts = request_part.split('"')[0].split(' ')

                        method = req_subparts[0] if len(req_subparts) > 0 else 'GET'
                        endpoint = req_subparts[1] if len(req_subparts) > 1 else '/'
                        status_code = int(parts[8]) if len(parts) > 8 and parts[8].isdigit() else 200

                        # Mencegah data duplikat masuk ke PostgreSQL
                        cur.execute(
                            "SELECT id FROM nginx_logs WHERE ip_address=%s AND timestamp=%s AND endpoint=%s",
                            (ip, timestamp, endpoint)
                        )
                        if not cur.fetchone():
                            # Eksekusi simpan data ke PostgreSQL
                            cur.execute(
                                "INSERT INTO nginx_logs (ip_address, timestamp, method, endpoint, status_code, user_agent) VALUES (%s, %s, %s, %s, %s, %s)",
                                (ip, timestamp, method, endpoint, status_code, "Nginx Log")
                            )
                    except Exception:
                        continue

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error syncing logs to DB: {e}")

@app.route('/')
def dashboard():
    # Lakukan ekstraksi & simpan log Nginx ke PostgreSQL setiap halaman ini diakses
    parse_and_sync_logs()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Mengambil statistik dari PostgreSQL
        cur.execute("SELECT COUNT(*) FROM nginx_logs;")
        total_logs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT ip_address) FROM nginx_logs;")
        unique_ips = cur.fetchone()[0]

        cur.execute("SELECT ip_address, method, endpoint, status_code, timestamp FROM nginx_logs ORDER BY id DESC LIMIT 10;")
        recent_visits = cur.fetchall()

        cur.close()
        conn.close()
    except Exception:
        total_logs, unique_ips, recent_visits = 0, 0, []

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Analytics - mpshub.my.id</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }
            .card { background: #1e293b; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: inline-block; width: 200px; }
            h1 { color: #38bdf8; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #1e293b; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #334155; }
            th { background: #334155; color: #38bdf8; }
        </style>
    </head>
    <body>
        <h1>mpshub.my.id - Visitor Analytics</h1>
        <div class="card">
            <h3>Total Hits</h3>
            <h2>{{ total_logs }}</h2>
        </div>
        <div class="card">
            <h3>Unique IPs</h3>
            <h2>{{ unique_ips }}</h2>
        </div>

        <h2>10 Kunjungan Terakhir ke mpshub.my.id</h2>
        <table>
            <tr>
                <th>IP Address</th>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Status</th>
                <th>Waktu</th>
            </tr>
            {% for log in recent_visits %}
            <tr>
                <td>{{ log[0] }}</td>
                <td>{{ log[1] }}</td>
                <td>{{ log[2] }}</td>
                <td>{{ log[3] }}</td>
                <td>{{ log[4] }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html_template, total_logs=total_logs, unique_ips=unique_ips, recent_visits=recent_visits)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
