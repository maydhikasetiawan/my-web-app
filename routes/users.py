from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from routes.auth import login_required, roles_required
from database.db import get_db_connection

users_bp = Blueprint('users', __name__, url_prefix='/users')

# --- DAFTAR USER (KHUSUS SUPER ADMIN) ---
@users_bp.route('/')
@login_required
@roles_required('admin')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role, department, created_at FROM users ORDER BY id ASC;")
    users_list = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('users/index.html', users=users_list, active_page='users')

# --- TAMBAH USER BARU ---
@users_bp.route('/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def add():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        role = request.form.get('role')
        department = request.form.get('department')

        try:
            password_hash = generate_password_hash(password)
            cur.execute("""
                INSERT INTO users (username, email, password_hash, role, department)
                VALUES (%s, %s, %s, %s, %s);
            """, (username, email, password_hash, role, department))
            conn.commit()
            cur.close()
            conn.close()
            flash(f"User '{username}' berhasil ditambahkan!", "success")
            return redirect(url_for('users.index'))
        except Exception as e:
            conn.rollback()
            flash("Username atau Email sudah terdaftar!", "danger")

    cur.execute("SELECT * FROM departments ORDER BY name ASC;")
    departments = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('users/add.html', departments=departments, active_page='users')

# --- HAPUS USER ---
@users_bp.route('/delete/<int:user_id>')
@login_required
@roles_required('admin')
def delete(user_id):
    if user_id == session.get('user_id'):
        flash("Anda tidak bisa menghapus akun Anda sendiri yang sedang login!", "danger")
        return redirect(url_for('users.index'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("User berhasil dihapus.", "success")
    return redirect(url_for('users.index'))

# --- MANAJEMEN DEPARTEMEN MODULAR ---
@users_bp.route('/departments', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def departments():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        dept_name = request.form.get('department_name', '').strip()
        if dept_name:
            try:
                cur.execute("INSERT INTO departments (name) VALUES (%s);", (dept_name,))
                conn.commit()
                flash(f"Departemen '{dept_name}' berhasil ditambahkan!", "success")
            except Exception as e:
                conn.rollback()
                flash("Departemen sudah ada!", "danger")

    cur.execute("SELECT * FROM departments ORDER BY name ASC;")
    dept_list = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('users/departments.html', departments=dept_list, active_page='users')

@users_bp.route('/departments/delete/<int:dept_id>')
@login_required
@roles_required('admin')
def delete_department(dept_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM departments WHERE id = %s;", (dept_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Departemen berhasil dihapus.", "success")
    return redirect(url_for('users.departments'))
