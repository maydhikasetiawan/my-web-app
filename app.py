import os
import re
import psycopg2
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

DB_HOST = os.getenv('DB_HOST', 'postgres-server')
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
LOG_FILE_PATH = '/var/log/nginx/access.log'

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=5432
    )

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
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
        print(f"Error init DB: {e}")

init_db()

def parse_and_sync_logs():
    if not os.path.exists(LOG_FILE_PATH):
        return

    # Regex untuk membaca format Nginx Access Log
    log_pattern = re.compile(
        r'(?P<ip>[\d\.]+) - - \[(?P<time>[^\]]+)\] "(?P<method>\w+) (?P<endpoint>[^\s]+) [^"]+" (?P<status>\d+) \d+ "[^"]*" "(?P<agent>[^"]*)"'
    )

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        with open(LOG_FILE_PATH, 'r') as f:
            for line in f.readlines()[-100:]:  # Baca 100 baris log terakhir
                match = log_pattern.match(line)
                if match:
                    data = match.groupdict()
                    # Cek apakah log ini sudah ada agar tidak duplikat
                    cur.execute(
                        "SELECT id FROM nginx_logs WHERE ip_address=%s AND timestamp=%s AND endpoint=%s",
                        (data['ip'], data['time'], data['endpoint'])
                    )
                    if not cur.fetchone():
                        cur.execute(
                            "INSERT INTO nginx_logs (ip_address, timestamp, method, endpoint, status_code, user_agent) VALUES (%s, %s, %s, %s, %s, %s)",
                            (data['ip'], data['time'], data['method'], data['endpoint'], int(data['status']), data['agent'])
                        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error sync logs: {e}")

@app.route('/')
def dashboard():
    parse_and_sync_logs()
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM nginx_logs;")
        total_logs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT ip_address) FROM nginx_logs;")
        unique_ips = cur.fetchone()[0]

        cur.execute("SELECT ip_address, method, endpoint, status_code, timestamp FROM nginx_logs ORDER BY id DESC LIMIT 10;")
        recent_visits = cur.fetchall()

        cur.close()
        conn.close()
    except Exception as e:
        total_logs, unique_ips, recent_visits = 0, 0, []

    # Tampilan HTML Dashboard Sederhana
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
