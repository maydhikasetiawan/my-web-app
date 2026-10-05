from flask import Blueprint, render_template, request, redirect, url_for, session
from routes.auth import login_required, write_access_required
from database.db import get_db_connection

assets_bp = Blueprint('assets', __name__, url_prefix='/assets')

@assets_bp.route('/')
@login_required
def index():
    search_query = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()

    if search_query:
        cur.execute("""
            SELECT * FROM assets
            WHERE name ILIKE %s OR asset_tag ILIKE %s OR ip_address ILIKE %s OR location ILIKE %s
            ORDER BY id DESC;
        """, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cur.execute("SELECT * FROM assets ORDER BY id DESC;")

    assets_list = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('assets/index.html', assets=assets_list, search_query=search_query, active_page='assets')

@assets_bp.route('/add', methods=['GET', 'POST'])
@login_required
@write_access_required
def add():
    if request.method == 'POST':
        asset_tag = request.form.get('asset_tag')
        name = request.form.get('name')
        category = request.form.get('category')
        ip_address = request.form.get('ip_address')
        mac_address = request.form.get('mac_address')
        status = request.form.get('status')
        location = request.form.get('location')
        notes = request.form.get('notes')

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO assets (asset_tag, name, category, ip_address, mac_address, status, location, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (asset_tag, name, category, ip_address, mac_address, status, location, notes))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('assets.index'))
        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            return f"Error adding asset: {e}"

    return render_template('assets/add.html', active_page='assets')

@assets_bp.route('/delete/<int:asset_id>')
@login_required
@write_access_required
def delete(asset_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM assets WHERE id = %s;", (asset_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('assets.index'))
