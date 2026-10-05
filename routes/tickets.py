from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from routes.auth import login_required, write_access_required
from database.db import get_db_connection
from datetime import datetime

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')

def generate_ticket_code():
    today_str = datetime.now().strftime('%Y%m%d')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM tickets WHERE ticket_code LIKE %s;", (f'TCK-{today_str}-%',))
    count = cur.fetchone()['count'] + 1
    cur.close()
    conn.close()
    return f"TCK-{today_str}-{count:03d}"

@tickets_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    search_query = request.args.get('q', '')

    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT * FROM tickets WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)

    if search_query:
        query += " AND (ticket_code ILIKE %s OR title ILIKE %s OR created_by ILIKE %s)"
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    query += " ORDER BY id DESC;"
    cur.execute(query, tuple(params))
    tickets_list = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('tickets/index.html', tickets=tickets_list, status_filter=status_filter, search_query=search_query, active_page='tickets')

@tickets_bp.route('/add', methods=['GET', 'POST'])
@login_required
@write_access_required
def add():
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        priority = request.form.get('priority')
        description = request.form.get('description')
        ticket_code = generate_ticket_code()
        created_by = session.get('username')

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO tickets (ticket_code, title, category, priority, status, description, created_by)
                VALUES (%s, %s, %s, %s, 'Open', %s, %s);
            """, (ticket_code, title, category, priority, description, created_by))
            conn.commit()
            cur.close()
            conn.close()
            flash(f"Tiket {ticket_code} berhasil dibuat!", "success")
            return redirect(url_for('tickets.index'))
        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            return f"Error creating ticket: {e}"

    return render_template('tickets/add.html', active_page='tickets')

@tickets_bp.route('/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def detail(ticket_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST' and session.get('role') != 'guest':
        new_status = request.form.get('status')
        resolution_note = request.form.get('resolution_note', '').strip()
        user_now = session.get('username')

        if new_status in ['Resolved', 'Closed']:
            cur.execute("""
                UPDATE tickets
                SET status = %s,
                    resolution_note = %s,
                    resolved_by = %s,
                    resolved_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (new_status, resolution_note, user_now, ticket_id))
        else:
            cur.execute("""
                UPDATE tickets
                SET status = %s,
                    resolution_note = %s
                WHERE id = %s;
            """, (new_status, resolution_note, ticket_id))

        conn.commit()
        flash("Status dan laporan penyelesaian tiket berhasil diperbarui!", "success")

    cur.execute("SELECT * FROM tickets WHERE id = %s;", (ticket_id,))
    ticket = cur.fetchone()
    cur.close()
    conn.close()

    if not ticket:
        return "Tiket tidak ditemukan", 404

    return render_template('tickets/detail.html', ticket=ticket, active_page='tickets')
