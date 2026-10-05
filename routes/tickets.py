from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from routes.auth import login_required, roles_required
from database.db import get_db_connection
from datetime import datetime

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')

@tickets_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    search_query = request.args.get('q', '')
    user_role = session.get('role', 'guest')
    username = session.get('username')

    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT * FROM tickets WHERE is_deleted = FALSE"
    params = []

    # REGULAR USER HANYA BISA MELIHAT TIKET MILIKNYA SENDIRI
    if user_role == 'user':
        query += " AND created_by = %s"
        params.append(username)

    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)

    if search_query:
        query += " AND (ticket_code ILIKE %s OR title ILIKE %s)"
        params.append(f'%{search_query}%')

    query += " ORDER BY id DESC;"
    cur.execute(query, tuple(params))
    tickets_list = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('tickets/index.html', tickets=tickets_list, status_filter=status_filter, search_query=search_query, active_page='tickets')

@tickets_bp.route('/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'it', 'user') # Admin, IT, dan User bisa membuat tiket
def add():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        priority = request.form.get('priority')
        description = request.form.get('description')
        ticket_code = generate_ticket_code()

        # Ambil username dan departemen pelapor secara otomatis dari Session
        created_by = session.get('username')
        user_dept = session.get('department', 'IT')

        try:
            cur.execute("""
                INSERT INTO tickets (ticket_code, title, category, priority, status, description, created_by, department)
                VALUES (%s, %s, %s, %s, 'Open', %s, %s, %s);
            """, (ticket_code, title, category, priority, description, created_by, user_dept))
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

    # Ambil Kategori Dinamis dari Database
    cur.execute("SELECT * FROM ticket_categories ORDER BY name ASC;")
    categories = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('tickets/add.html', categories=categories, active_page='tickets')

@tickets_bp.route('/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def detail(ticket_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE id = %s AND is_deleted = FALSE;", (ticket_id,))
    ticket = cur.fetchone()

    if not ticket:
        cur.close()
        conn.close()
        return "Tiket tidak ditemukan", 404

    user_role = session.get('role')
    username = session.get('username')

    # Proteksi: Regular User hanya bisa membuka detail tiket miliknya
    if user_role == 'user' and ticket['created_by'] != username:
        cur.close()
        conn.close()
        flash("Akses ditolak! Anda tidak berhak melihat tiket pengguna lain.", "danger")
        return redirect(url_for('tickets.index'))

    # Proteksi: Pengubahan status/solusi hanya untuk Admin dan IT Support
    if request.method == 'POST':
        if user_role not in ['admin', 'it']:
            flash("Akses ditolak! Hanya Tim IT & Admin yang dapat memperbarui status tiket.", "danger")
            cur.close()
            conn.close()
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))

        if ticket['status'] in ['Resolved', 'Closed']:
            flash("Tiket ini telah selesai/ditutup dan tidak dapat diubah lagi!", "danger")
            cur.close()
            conn.close()
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))

        new_status = request.form.get('status')
        resolution_note = request.form.get('resolution_note', '').strip()
        user_now = session.get('username')

        if new_status in ['Resolved', 'Closed']:
            cur.execute("""
                UPDATE tickets
                SET status = %s, resolution_note = %s, resolved_by = %s, resolved_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (new_status, resolution_note, user_now, ticket_id))
        else:
            cur.execute("""
                UPDATE tickets
                SET status = %s, resolution_note = %s
                WHERE id = %s;
            """, (new_status, resolution_note, ticket_id))

        conn.commit()
        cur.close()
        conn.close()
        flash("Status dan laporan penyelesaian tiket berhasil diperbarui!", "success")
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    cur.close()
    conn.close()
    return render_template('tickets/detail.html', ticket=ticket, active_page='tickets')
