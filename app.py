import os
from flask import Flask
from database.db import init_db
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.assets import assets_bp
from routes.tickets import tickets_bp
from routes.reports import reports_bp

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'mps-ithub-super-secret-key-2026')

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(assets_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(reports_bp)

@app.before_request
def ensure_db_initialized():
    if not getattr(app, '_got_first_request', False):
        init_db()
        app._got_first_request = True

@app.route('/health')
def health():
    return {"status": "healthy"}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
