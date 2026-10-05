from flask import Blueprint, render_template, session
from routes.auth import login_required
from database.db import get_db_connection

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor()

    # Total Aset Aktif
    cur.execute("SELECT COUNT(*) as count FROM assets WHERE is_deleted = FALSE;")
    total_assets = cur.fetchone()['count']

    # Tiket Open / In Progress
    cur.execute("SELECT COUNT(*) as count FROM tickets WHERE status IN ('Open', 'In Progress') AND is_deleted = FALSE;")
    open_tickets = cur.fetchone()['count']

    # Hitung Persentase Services Online dari Uptime Monitor
    cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = 'UP' THEN 1 ELSE 0 END) as up_count FROM monitors;")
    monitor_stats = cur.fetchone()

    total_monitors = monitor_stats['total'] or 0
    up_monitors = monitor_stats['up_count'] or 0

    if total_monitors > 0:
        uptime_percentage = round((up_monitors / total_monitors) * 100, 1)
    else:
        uptime_percentage = 100.0  # Default 100% jika belum ada monitor

    cur.close()
    conn.close()

    return render_template('dashboard.html',
                           total_assets=total_assets,
                           open_tickets=open_tickets,
                           uptime_percentage=uptime_percentage,
                           active_page='dashboard')
