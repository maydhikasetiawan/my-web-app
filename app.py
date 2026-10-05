import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'mps-ithub-super-secret-key-2026')

# Konfigurasi Database PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'postgres-server')
DB_NAME = os.getenv('DB_NAME', 'db_monitoring')
DB_USER = os.getenv('DB_USER', 'admin_server')
DB_PASS = os.getenv('DB_PASS', 'PasswordSuperAman123')

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=5432,
        cursor_factory=RealDictCursor
    )

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Tabel Users
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # 2. Tabel Assets (IPAM & Inventory)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                id SERIAL PRIMARY KEY,
                asset_tag VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                ip_address VARCHAR(45),
                mac_address VARCHAR(45),
                status VARCHAR(20) DEFAULT 'Active',
                location VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # 3. Tabel Tickets (Service Desk)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id SERIAL PRIMARY KEY,
                ticket_code VARCHAR(20) UNIQUE NOT NULL,
                title VARCHAR(150) NOT NULL,
                category VARCHAR(50) NOT NULL,
                priority VARCHAR(20) DEFAULT 'Medium',
                status VARCHAR(20) DEFAULT 'Open',
                description TEXT,
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # 4. Tabel Service Monitors
        cur.execute('''
            CREATE TABLE IF NOT EXISTS service_monitors (
                id SERIAL PRIMARY KEY,
                service_name VARCHAR(100) NOT NULL,
                target_url VARCHAR(255) NOT NULL,
                last_status VARCHAR(20) DEFAULT 'Unknown',
                response_time_ms INT DEFAULT 0,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Buat Akun Default (Admin & Guest) Jika Belum Ada
        cur.execute("SELECT * FROM users WHERE username = 'admin';")
        if not cur.fetchone():
            admin_pass = generate_password_hash('AdminPass123!')
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s);",
                ('admin', 'admin@mpshub.my.id', admin_pass, 'admin')
            )

        cur.execute("SELECT * FROM users WHERE username = 'guest';")
        if not cur.fetchone():
            guest_pass = generate_password_hash('GuestPass123!')
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s);",
                ('guest', 'guest@mpshub.my.id', guest_pass, 'guest')
            )

        conn.commit()
        cur.close()
        conn.close()
        print("Database & Default Users initialized successfully.")
    except Exception as e:
        print(f"Error initializing DB: {e}")

init_db()

# Decorator untuk Proteksi Login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Route Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = %s;", (username,))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                return redirect(url_for('dashboard'))
            else:
                error = "Username atau password salah!"
        except Exception as e:
            error = f"Database error: {e}"

    login_html = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - MPS Operational IT Hub</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            body { background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
            .login-card { background: #1e293b; padding: 40px; border-radius: 12px; width: 100%; max-width: 400px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; text-align: center; }
            .logo-container { margin-bottom: 20px; }
            .logo-placeholder { width: 80px; height: 80px; margin: 0 auto 10px; background: linear-gradient(135deg, #38bdf8, #10b981); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: #0f172a; }
            h2 { font-size: 22px; color: #38bdf8; margin-bottom: 5px; }
            p.subtitle { font-size: 13px; color: #94a3b8; margin-bottom: 25px; }
            .form-group { text-align: left; margin-bottom: 18px; }
            label { display: block; font-size: 13px; color: #cbd5e1; margin-bottom: 6px; }
            input { width: 100%; padding: 10px 14px; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #fff; font-size: 14px; }
            input:focus { border-color: #38bdf8; outline: none; }
            button { width: 100%; padding: 12px; background: #38bdf8; border: none; border-radius: 6px; color: #0f172a; font-weight: bold; font-size: 15px; cursor: pointer; transition: 0.2s; }
            button:hover { background: #0284c7; color: #fff; }
            .alert { background: #ef444422; border: 1px solid #ef4444; color: #fca5a5; padding: 10px; border-radius: 6px; font-size: 13px; margin-bottom: 15px; }
            .demo-info { margin-top: 20px; font-size: 11px; color: #64748b; border-top: 1px solid #334155; padding-top: 15px; text-align: left; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <div class="logo-container">
                <div class="logo-placeholder">🛡️</div>
                <h2>MPS-ITHub</h2>
                <p class="subtitle">IT Service Desk & Infrastructure Portal</p>
            </div>

            {% if error %}
            <div class="alert">{{ error }}</div>
            {% endif %}

            <form method="POST">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" name="username" required placeholder="Masukkan username">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" required placeholder="Masukkan password">
                </div>
                <button type="submit">Sign In</button>
            </form>

            <div class="demo-info">
                <strong>Default Credentials:</strong><br>
                • Admin: <code>admin</code> / <code>AdminPass123!</code><br>
                • Guest: <code>guest</code> / <code>GuestPass123!</code>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(login_html, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard - MPS-ITHub</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
            body { background: #0f172a; color: #f8fafc; display: flex; height: 100vh; }
            .sidebar { width: 250px; background: #1e293b; border-right: 1px solid #334155; padding: 20px; display: flex; flex-direction: column; }
            .brand { font-size: 20px; font-weight: bold; color: #38bdf8; margin-bottom: 30px; display: flex; align-items: center; gap: 10px; }
            .nav-menu { list-style: none; flex: 1; }
            .nav-item { margin-bottom: 10px; }
            .nav-link { color: #94a3b8; text-decoration: none; padding: 10px; border-radius: 6px; display: block; font-size: 14px; }
            .nav-link.active, .nav-link:hover { background: #334155; color: #38bdf8; }
            .main-content { flex: 1; padding: 30px; overflow-y: auto; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #334155; padding-bottom: 15px; }
            .user-badge { background: #334155; padding: 6px 12px; border-radius: 20px; font-size: 13px; color: #10b981; }
            .role-guest { color: #f59e0b; }
            .btn-logout { background: #ef4444; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 13px; }
            .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .card { background: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 8px; }
            .card h4 { color: #94a3b8; font-size: 13px; margin-bottom: 10px; }
            .card h2 { color: #38bdf8; font-size: 28px; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="brand">🛡️ MPS-ITHub</div>
            <ul class="nav-menu">
                <li class="nav-item"><a href="#" class="nav-link active">📊 Dashboard</a></li>
                <li class="nav-item"><a href="#" class="nav-link">🖥️ IT Assets (IPAM)</a></li>
                <li class="nav-item"><a href="#" class="nav-link">🎫 Service Desk</a></li>
                <li class="nav-item"><a href="#" class="nav-link">🌐 Uptime Monitor</a></li>
                {% if session['role'] == 'admin' %}
                <li class="nav-item"><a href="#" class="nav-link">👥 User Management</a></li>
                {% endif %}
            </ul>
        </div>
        <div class="main-content">
            <div class="header">
                <h2>Operational Dashboard</h2>
                <div>
                    Selamat datang, <strong>{{ session['username'] }}</strong>
                    <span class="user-badge {% if session['role'] == 'guest' %}role-guest{% endif %}">
                        [{{ session['role'] | upper }}]
                    </span>
                    <a href="{{ url_for('logout') }}" class="btn-logout" style="margin-left: 15px;">Logout</a>
                </div>
            </div>

            {% if session['role'] == 'guest' %}
            <div style="background: #f59e0b22; border: 1px solid #f59e0b; color: #fbbf24; padding: 12px; border-radius: 6px; margin-bottom: 20px; font-size: 13px;">
                ℹ️ Anda masuk sebagai <strong>Guest (Read-Only)</strong>. Anda dapat melihat seluruh status infrastruktur tetapi tidak memiliki akses untuk menambah atau mengubah data.
            </div>
            {% endif %}

            <div class="card-grid">
                <div class="card">
                    <h4>TOTAL ASSETS</h4>
                    <h2>0</h2>
                </div>
                <div class="card">
                    <h4>OPEN TICKETS</h4>
                    <h2>0</h2>
                </div>
                <div class="card">
                    <h4>SERVICES ONLINE</h4>
                    <h2>100%</h2>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(dashboard_html)

@app.route('/health')
def health():
    return {"status": "healthy"}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
