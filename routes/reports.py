import csv
import io
from flask import Blueprint, render_template, request, Response, session, flash, redirect, url_for
from routes.auth import login_required
from database.db import get_db_connection
from datetime import datetime

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor()

    # Ambil kategori tiket untuk dropdown filter
    cur.execute("SELECT * FROM ticket_categories ORDER BY name ASC;")
    ticket_categories = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('reports/index.html', ticket_categories=ticket_categories, active_page='reports')

# --- EXPORT LAPORAN ASSETS (IPAM) ---
@reports_bp.route('/export/assets')
@login_required
def export_assets():
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    include_deleted = request.args.get('include_deleted', 'false')

    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT * FROM assets WHERE 1=1"
    params = []

    if include_deleted != 'true':
        query += " AND is_deleted = FALSE"

    if category:
        query += " AND category = %s"
        params.append(category)

    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY id DESC;"
    cur.execute(query, tuple(params))
    assets = cur.fetchall()
    cur.close()
    conn.close()

    # Generator File CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header Kolom Excel
    writer.writerow([
        'ID', 'Asset Tag', 'Nama Perangkat', 'Kategori', 'IP Address',
        'MAC Address', 'Status', 'Lokasi', 'Catatan', 'Tanggal Terdaftar',
        'Terakhir Diperbarui', 'Diperbarui Oleh', 'Status Penghapusan', 'Alasan Penghapusan'
    ])

    for a in assets:
        created_str = a['created_at'].strftime('%Y-%m-%d %H:%M:%S') if a['created_at'] else ''
        updated_str = a['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if a['updated_at'] else ''
        deleted_status = 'Terhapus/Archived' if a['is_deleted'] else 'Aktif'

        writer.writerow([
            a['id'],
            a['asset_tag'],
            a['name'],
            a['category'],
            a['ip_address'] or '',
            a['mac_address'] or '',
            a['status'],
            a['location'] or '',
            a['notes'] or '',
            created_str,
            updated_str,
            a['updated_by'] or '',
            deleted_status,
            a['delete_reason'] or ''
        ])

    filename = f"Laporan_Aset_IT_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    # Encoded UTF-8-SIG agar Microsoft Excel membuka titik koma/koma dengan rapi
    csv_data = '\ufeff' + output.getvalue()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# --- EXPORT LAPORAN SERVICE DESK (TICKETS) ---
@reports_bp.route('/export/tickets')
@login_required
def export_tickets():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    category = request.args.get('category', '')
    status = request.args.get('status', '')

    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT * FROM tickets WHERE is_deleted = FALSE"
    params = []

    if start_date:
        query += " AND created_at >= %s"
        params.append(f"{start_date} 00:00:00")

    if end_date:
        query += " AND created_at <= %s"
        params.append(f"{end_date} 23:59:59")

    if category:
        query += " AND category = %s"
        params.append(category)

    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY id DESC;"
    cur.execute(query, tuple(params))
    tickets = cur.fetchall()
    cur.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header Kolom Excel
    writer.writerow([
        'ID', 'Kode Tiket', 'Judul Masalah', 'Kategori', 'Prioritas',
        'Status', 'Deskripsi Masalah', 'Pelapor', 'Tanggal Laporan',
        'Catatan Solusi / Resolution Note', 'Diselesaikan Oleh', 'Tanggal Selesai'
    ])

    for t in tickets:
        created_str = t['created_at'].strftime('%Y-%m-%d %H:%M:%S') if t['created_at'] else ''
        resolved_str = t['resolved_at'].strftime('%Y-%m-%d %H:%M:%S') if t['resolved_at'] else ''

        writer.writerow([
            t['id'],
            t['ticket_code'],
            t['title'],
            t['category'],
            t['priority'],
            t['status'],
            t['description'],
            t['created_by'],
            created_str,
            t['resolution_note'] or '',
            t['resolved_by'] or '',
            resolved_str
        ])

    filename = f"Laporan_Service_Desk_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    csv_data = '\ufeff' + output.getvalue()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
