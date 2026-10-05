from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
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

    query = "SELECT * FROM tickets WHERE is_deleted = FALSE"
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
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        priority = request.form.get('priority')
        description = request.form.get('description')
        ticket_code = generate_ticket_code()
        created_by = session.get('username')

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

    if request.method == 'POST' and session.get('role') != 'guest':
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
        cur.close()
        conn.close()
        flash("Status dan laporan penyelesaian tiket berhasil diperbarui!", "success")
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    cur.close()
    conn.close()
    return render_template('tickets/detail.html', ticket=ticket, active_page='tickets')

# --- MANAJEMEN KATEGORI TIKET (KHUSUS ADMIN) ---
@tickets_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    if session.get('role') != 'admin':
        flash("Akses ditolak! Hanya Super Admin yang dapat mengelola kategori.", "danger")
        return redirect(url_for('tickets.index'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        new_category = request.form.get('category_name', '').strip()
        if new_category:
            try:
                cur.execute("INSERT INTO ticket_categories (name) VALUES (%s);", (new_category,))
                conn.commit()
                flash(f"Kategori '{new_category}' berhasil ditambahkan!", "success")
            except Exception as e:
                conn.rollback()
                flash("Kategori sudah ada atau terjadi kesalahan.", "danger")

    cur.execute("SELECT * FROM ticket_categories ORDER BY name ASC;")
    categories = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('tickets/categories.html', categories=categories, active_page='tickets')

@tickets_bp.route('/categories/delete/<int:category_id>')
@login_required
def delete_category(category_id):
    if session.get('role') != 'admin':
        flash("Akses ditolak!", "danger")
        return redirect(url_for('tickets.index'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ticket_categories WHERE id = %s;", (category_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Kategori berhasil dihapus.", "success")
    return redirect(url_for('tickets.manage_categories'))

@tickets_bp.route('/delete-permanent/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def delete_permanent(ticket_id):
    if session.get('role') != 'admin':
        flash("Akses ditolak!", "danger")
        return redirect(url_for('tickets.index'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE id = %s;", (ticket_id,))
    ticket = cur.fetchone()

    if not ticket:
        cur.close()
        conn.close()
        return "Tiket tidak ditemukan", 404

    error = None
    if request.method == 'POST':
        input_password = request.form.get('confirm_password', '')
        user_id = session.get('user_id')

        cur.execute("SELECT password_hash FROM users WHERE id = %s;", (user_id,))
        admin_data = cur.fetchone()

        if not admin_data or not check_password_hash(admin_data['password_hash'], input_password):
            error = "Password Admin salah!"
        else:
            cur.execute("DELETE FROM tickets WHERE id = %s;", (ticket_id,))
            conn.commit()
            cur.close()
            conn.close()
            flash(f"Tiket {ticket['ticket_code']} berhasil dihapus permanen.", "danger")
            return redirect(url_for('tickets.index'))

    cur.close()
    conn.close()
    return render_template('tickets/delete_permanent.html', ticket=ticket, error=error, active_page='tickets')
