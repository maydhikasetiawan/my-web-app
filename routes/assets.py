from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from routes.auth import login_required, roles_required
from database.db import get_db_connection
from datetime import datetime

assets_bp = Blueprint('assets', __name__, url_prefix='/assets')

# ... (Fungsi calculate_age tetap sama) ...

@assets_bp.route('/')
@login_required
@roles_required('admin', 'it', 'guest') # User biasa tidak mengakses daftar aset
def index():
    # ... (Logika index tetap sama) ...
    pass

@assets_bp.route('/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'it') # Khusus Admin & IT Staff
def add():
    # ... (Logika add tetap sama) ...
    pass

@assets_bp.route('/edit/<int:asset_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'it') # Khusus Admin & IT Staff
def edit(asset_id):
    # ... (Logika edit tetap sama) ...
    pass

@assets_bp.route('/delete/<int:asset_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'it') # Soft delete oleh Admin & IT
def delete(asset_id):
    # ... (Logika soft delete tetap sama) ...
    pass

@assets_bp.route('/hard-delete/<int:asset_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin') # Khusus Super Admin
def hard_delete(asset_id):
    # ... (Logika hard delete tetap sama) ...
    pass
