from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from routes.auth import login_required, write_access_required
from database.db import get_db_connection
from datetime import datetime

assets_bp = Blueprint('assets', __name__, url_prefix='/assets')

def calculate_age(created_at):
    if not created_at:
        return "-"
    now = datetime.now()
    diff = now - created_at
    days = diff.days

    if days < 1:
        return "Hari ini"
    elif days < 30:
        return f"{days} Hari"
    elif days < 365:
        months = days // 30
        remaining_days = days % 30
        return f"{months} Bulan {remaining_days} Hari"
    else:
        years = days // 365
        remaining_months = (days % 365) // 30
        return f"{years} Tahun {remaining_months} Bulan"

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

    # Hitung umur perangkat untuk setiap aset
    for asset in assets_list:
        asset['age'] = calculate_age(asset['created_at'])

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
        user_now = session.get('username')

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO assets (asset_tag, name, category, ip_address, mac_address, status, location, notes, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (asset_tag, name, category, ip_address, mac_address, status, location, notes, user_now))
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

@assets_bp.route('/edit/<int:asset_id>', methods=['GET', 'POST'])
@login_required
@write_access_required
def edit(asset_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        ip_address = request.form.get('ip_address')
        mac_address = request.form.get('mac_address')
        status = request.form.get('status')
        location = request.form.get('location')
        notes = request.form.get('notes')
        user_now = session.get('username')

        try:
            cur.execute("""
                UPDATE assets
                SET ip_address = %s, mac_address = %s, status = %s, location = %s, notes = %s,
                    updated_at = CURRENT_TIMESTAMP, updated_by = %s
                WHERE id = %s;
            """, (ip_address, mac_address, status, location, notes, user_now, asset_id))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('assets.index'))
        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            return f"Error updating asset: {e}"

    cur.execute("SELECT * FROM assets WHERE id = %s;", (asset_id,))
    asset = cur.fetchone()
    cur.close()
    conn.close()

    if not asset:
        return "Asset tidak ditemukan", 404

    return render_template('assets/edit.html', asset=asset, active_page='assets')

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
