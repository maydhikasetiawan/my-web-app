from flask import Blueprint, render_template
from routes.auth import login_required
from database.db import get_db_connection

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Total Aset Aktif
    cur.execute("SELECT COUNT(*) as total FROM assets WHERE is_deleted = FALSE;")
    total_assets = cur.fetchone()['total']

    # 2. Total Tiket Terbuka (Open + In Progress)
    cur.execute("SELECT COUNT(*) as total FROM tickets WHERE status IN ('Open', 'In Progress') AND is_deleted = FALSE;")
    open_tickets = cur.fetchone()['total']

    cur.close()
    conn.close()

    return render_template('dashboard.html', total_assets=total_assets, open_tickets=open_tickets, active_page='dashboard')
