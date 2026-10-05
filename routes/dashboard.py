from flask import Blueprint, render_template
from routes.auth import login_required
from database.db import get_db_connection

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM assets;")
    total_assets = cur.fetchone()['total']
    cur.close()
    conn.close()

    return render_template('dashboard.html', total_assets=total_assets, active_page='dashboard')
