"""
TTS Guard — Database Layer
SQLite schema (8 tables) and all query functions.
"""

import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_guard.db")

_db_initialized = False


def get_connection():
    """Return a sqlite3 connection with Row factory for dict-like access."""
    global _db_initialized
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if not _db_initialized:
        # Set flag first to prevent recursion (init_db also calls get_connection)
        _db_initialized = True
        _ensure_tables_exist()
    return conn


def _ensure_tables_exist():
    """Auto-create tables and seed if DB is empty (handles direct page navigation)."""
    init_db()
    if not has_data():
        from seed_data import seed
        seed()


def init_db():
    """Create all 8 tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            area TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            visits_per_year INTEGER DEFAULT 4,
            annual_value REAL NOT NULL,
            payment_terms TEXT DEFAULT 'quarterly',
            status TEXT DEFAULT 'active',
            FOREIGN KEY (building_id) REFERENCES buildings(id)
        );

        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'OK',
            FOREIGN KEY (building_id) REFERENCES buildings(id)
        );

        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            inspection_date TEXT NOT NULL,
            technician TEXT NOT NULL,
            items_checked INTEGER DEFAULT 0,
            items_passed INTEGER DEFAULT 0,
            items_failed INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (building_id) REFERENCES buildings(id)
        );

        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT NOT NULL UNIQUE,
            client_id INTEGER NOT NULL,
            building_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'open',
            assigned_technician TEXT,
            inspection_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (building_id) REFERENCES buildings(id),
            FOREIGN KEY (inspection_id) REFERENCES inspections(id)
        );

        CREATE TABLE IF NOT EXISTS scheduled_inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            scheduled_date TEXT NOT NULL,
            assigned_technician TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (building_id) REFERENCES buildings(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            payment_date TEXT NOT NULL,
            amount REAL NOT NULL,
            method TEXT DEFAULT 'bank_transfer',
            reference_number TEXT,
            status TEXT DEFAULT 'received',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        );
    """)

    conn.commit()
    conn.close()


def reset_db():
    """Drop all tables and re-create."""
    conn = get_connection()
    cursor = conn.cursor()
    tables = [
        "payments", "scheduled_inspections", "complaints",
        "inspections", "equipment", "contracts", "buildings", "clients"
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()
    conn.close()
    init_db()


def has_data():
    """Check if the database has seed data."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clients")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


# ---------------------------------------------------------------------------
# TECHNICIANS (constant)
# ---------------------------------------------------------------------------
TECHNICIANS = [
    "Mohammed Al-Rashid",
    "Suresh Kumar",
    "Ahmed Mansoor",
    "Rajesh Nair",
    "Khalid Ibrahim",
]


# ---------------------------------------------------------------------------
# CLIENT QUERIES
# ---------------------------------------------------------------------------

def get_all_clients():
    """Return all clients as a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM clients ORDER BY name", conn)
    conn.close()
    return df


def get_client_by_id(client_id):
    """Return a single client as a dict."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_client_summary():
    """
    Return client summary: name, building count, equipment count,
    total annual value, overdue count.
    """
    today = date.today().isoformat()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            cl.id as client_id,
            cl.name as "Client",
            cl.short_name,
            COUNT(DISTINCT b.id) as "Buildings",
            COUNT(DISTINCT e.id) as "Equipment",
            COALESCE(SUM(DISTINCT c.annual_value), 0) as "Annual Value (AED)",
            (
                SELECT COUNT(DISTINCT b2.id)
                FROM buildings b2
                JOIN contracts c2 ON c2.building_id = b2.id AND c2.status = 'active'
                LEFT JOIN (
                    SELECT building_id, MAX(inspection_date) as last_date
                    FROM inspections GROUP BY building_id
                ) li ON li.building_id = b2.id
                LEFT JOIN scheduled_inspections si
                    ON si.building_id = b2.id AND si.status = 'scheduled'
                WHERE b2.client_id = cl.id
                AND si.id IS NULL
                AND (
                    li.last_date IS NULL
                    OR julianday(?) - julianday(li.last_date) > 365.0 / c2.visits_per_year
                )
            ) as overdue_count
        FROM clients cl
        LEFT JOIN buildings b ON b.client_id = cl.id
        LEFT JOIN contracts c ON c.building_id = b.id AND c.status = 'active'
        LEFT JOIN equipment e ON e.building_id = b.id
        GROUP BY cl.id
        ORDER BY "Annual Value (AED)" DESC
    """, conn, params=[today])
    conn.close()
    return df


# ---------------------------------------------------------------------------
# BUILDING QUERIES
# ---------------------------------------------------------------------------

def get_all_buildings():
    """Return all buildings with client info."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT b.*, cl.name as client_name, cl.short_name
        FROM buildings b
        JOIN clients cl ON cl.id = b.client_id
        ORDER BY cl.name, b.name
    """, conn)
    conn.close()
    return df


def get_buildings_by_client(client_id):
    """Return buildings for a specific client."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT b.*,
            (SELECT COUNT(*) FROM equipment e WHERE e.building_id = b.id) as equipment_count,
            (SELECT MAX(i.inspection_date) FROM inspections i WHERE i.building_id = b.id) as last_inspection,
            c.annual_value,
            c.visits_per_year,
            c.payment_terms
        FROM buildings b
        LEFT JOIN contracts c ON c.building_id = b.id AND c.status = 'active'
        WHERE b.client_id = ?
        ORDER BY b.name
    """, conn, params=[client_id])
    conn.close()
    return df


def get_building_details(building_id):
    """Return full details for a building."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, cl.name as client_name, cl.short_name,
            cl.contact_person, cl.phone, cl.email,
            c.annual_value, c.visits_per_year, c.start_date, c.end_date,
            c.id as contract_id, c.payment_terms,
            (SELECT COUNT(*) FROM equipment e WHERE e.building_id = b.id) as equipment_count
        FROM buildings b
        JOIN clients cl ON cl.id = b.client_id
        LEFT JOIN contracts c ON c.building_id = b.id AND c.status = 'active'
        WHERE b.id = ?
    """, (building_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# INSPECTION QUERIES
# ---------------------------------------------------------------------------

def _get_inspection_status_query():
    """Return the base query for computing building inspection status."""
    return """
        SELECT
            b.id as building_id,
            b.name as building_name,
            b.area,
            cl.id as client_id,
            cl.name as client_name,
            cl.short_name,
            c.annual_value,
            c.visits_per_year,
            c.id as contract_id,
            (SELECT COUNT(*) FROM equipment e WHERE e.building_id = b.id) as equipment_count,
            li.last_date as last_inspection_date,
            CASE
                WHEN li.last_date IS NULL THEN 999
                ELSE CAST(julianday(?) - julianday(li.last_date) AS INTEGER)
            END as days_since_last,
            CASE
                WHEN li.last_date IS NULL THEN -999
                ELSE CAST(
                    (365.0 / c.visits_per_year) - (julianday(?) - julianday(li.last_date))
                    AS INTEGER
                )
            END as days_until_next
        FROM buildings b
        JOIN clients cl ON cl.id = b.client_id
        JOIN contracts c ON c.building_id = b.id AND c.status = 'active'
        LEFT JOIN (
            SELECT building_id, MAX(inspection_date) as last_date
            FROM inspections GROUP BY building_id
        ) li ON li.building_id = b.id
        LEFT JOIN scheduled_inspections si
            ON si.building_id = b.id AND si.status = 'scheduled'
    """


def get_overdue_inspections():
    """Return buildings where next inspection is overdue (not scheduled)."""
    today = date.today().isoformat()
    conn = get_connection()
    query = _get_inspection_status_query() + """
        WHERE si.id IS NULL
        AND (
            li.last_date IS NULL
            OR julianday(?) - julianday(li.last_date) > 365.0 / c.visits_per_year
        )
        ORDER BY days_since_last DESC
    """
    df = pd.read_sql_query(query, conn, params=[today, today, today])
    conn.close()
    return df


def get_upcoming_inspections(days=14):
    """Return buildings due within N days but not yet overdue."""
    today = date.today().isoformat()
    conn = get_connection()
    query = _get_inspection_status_query() + """
        WHERE si.id IS NULL
        AND li.last_date IS NOT NULL
        AND julianday(?) - julianday(li.last_date) <= 365.0 / c.visits_per_year
        AND (365.0 / c.visits_per_year) - (julianday(?) - julianday(li.last_date)) <= ?
        ORDER BY days_until_next ASC
    """
    df = pd.read_sql_query(query, conn, params=[today, today, today, today, days])
    conn.close()
    return df


def get_completed_this_month():
    """Return inspections completed in the current month."""
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT i.*, b.name as building_name, cl.name as client_name
        FROM inspections i
        JOIN buildings b ON b.id = i.building_id
        JOIN clients cl ON cl.id = b.client_id
        WHERE i.inspection_date >= ?
        ORDER BY i.inspection_date DESC
    """, conn, params=[month_start])
    conn.close()
    return df


def get_recent_inspections(days=30):
    """Return inspections from the last N days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT i.*, b.name as building_name, cl.name as client_name, cl.short_name
        FROM inspections i
        JOIN buildings b ON b.id = i.building_id
        JOIN clients cl ON cl.id = b.client_id
        WHERE i.inspection_date >= ?
        ORDER BY i.inspection_date DESC
    """, conn, params=[cutoff])
    conn.close()
    return df


def get_inspections_by_month(year, month):
    """Return inspections for a specific year/month."""
    month_start = f"{year}-{month:02d}-01"
    if month == 12:
        month_end = f"{year + 1}-01-01"
    else:
        month_end = f"{year}-{month + 1:02d}-01"
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT i.*, b.name as building_name, cl.name as client_name, cl.short_name
        FROM inspections i
        JOIN buildings b ON b.id = i.building_id
        JOIN clients cl ON cl.id = b.client_id
        WHERE i.inspection_date >= ? AND i.inspection_date < ?
        ORDER BY i.inspection_date DESC
    """, conn, params=[month_start, month_end])
    conn.close()
    return df


def insert_inspection(building_id, inspection_date, technician,
                      items_checked, items_passed, items_failed, notes):
    """Insert a new inspection record. Returns the new inspection ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inspections
            (building_id, inspection_date, technician, items_checked,
             items_passed, items_failed, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (building_id, inspection_date, technician,
          items_checked, items_passed, items_failed, notes))
    inspection_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inspection_id


# ---------------------------------------------------------------------------
# EQUIPMENT QUERIES
# ---------------------------------------------------------------------------

def get_equipment_by_building(building_id):
    """Return all equipment for a building."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT * FROM equipment
        WHERE building_id = ?
        ORDER BY type, id
    """, conn, params=[building_id])
    conn.close()
    return df


def get_equipment_grouped_by_type(building_id):
    """Return equipment grouped by type with counts."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT type, COUNT(*) as count, GROUP_CONCAT(id) as item_ids
        FROM equipment
        WHERE building_id = ?
        GROUP BY type
        ORDER BY type
    """, conn, params=[building_id])
    conn.close()
    return df


# ---------------------------------------------------------------------------
# COMPLAINT QUERIES
# ---------------------------------------------------------------------------

def get_all_complaints():
    """Return all complaints with client/building info."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT comp.*, cl.name as client_name, cl.short_name,
            b.name as building_name
        FROM complaints comp
        JOIN clients cl ON cl.id = comp.client_id
        JOIN buildings b ON b.id = comp.building_id
        ORDER BY comp.created_at DESC
    """, conn)
    conn.close()
    return df


def get_recent_complaints(limit=5):
    """Return the most recent complaints."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT comp.*, cl.name as client_name, cl.short_name,
            b.name as building_name
        FROM complaints comp
        JOIN clients cl ON cl.id = comp.client_id
        JOIN buildings b ON b.id = comp.building_id
        ORDER BY comp.created_at DESC
        LIMIT ?
    """, conn, params=[limit])
    conn.close()
    return df


def get_complaints_by_month(year, month):
    """Return complaints for a specific year/month."""
    month_start = f"{year}-{month:02d}-01"
    if month == 12:
        month_end = f"{year + 1}-01-01"
    else:
        month_end = f"{year}-{month + 1:02d}-01"
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT comp.*, cl.name as client_name, b.name as building_name
        FROM complaints comp
        JOIN clients cl ON cl.id = comp.client_id
        JOIN buildings b ON b.id = comp.building_id
        WHERE comp.created_at >= ? AND comp.created_at < ?
        ORDER BY comp.created_at DESC
    """, conn, params=[month_start, month_end])
    conn.close()
    return df


def insert_complaint(client_id, building_id, message, priority,
                     assigned_technician=None, inspection_id=None):
    """Insert a new complaint. Auto-generates ticket number. Returns ticket_number."""
    conn = get_connection()
    cursor = conn.cursor()
    year = date.today().year
    cursor.execute(
        "SELECT COUNT(*) FROM complaints WHERE ticket_number LIKE ?",
        (f"TTS-{year}-%",)
    )
    count = cursor.fetchone()[0]
    ticket_number = f"TTS-{year}-{count + 1:04d}"

    status = "assigned" if assigned_technician else "open"
    cursor.execute("""
        INSERT INTO complaints
            (ticket_number, client_id, building_id, message, priority,
             status, assigned_technician, inspection_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticket_number, client_id, building_id, message, priority,
          status, assigned_technician, inspection_id))
    conn.commit()
    conn.close()
    return ticket_number


# ---------------------------------------------------------------------------
# CONTRACT QUERIES
# ---------------------------------------------------------------------------

def get_active_contracts_count():
    """Return count of active contracts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM contracts WHERE status = 'active'")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_contract_by_building(building_id):
    """Return the active contract for a building."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM contracts
        WHERE building_id = ? AND status = 'active'
    """, (building_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# SCHEDULED INSPECTION QUERIES
# ---------------------------------------------------------------------------

def schedule_inspection(building_id, scheduled_date, assigned_technician):
    """Schedule an inspection for an overdue building."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scheduled_inspections
            (building_id, scheduled_date, assigned_technician)
        VALUES (?, ?, ?)
    """, (building_id, scheduled_date, assigned_technician))
    conn.commit()
    conn.close()


def get_scheduled_inspections():
    """Return all scheduled (not yet completed) inspections."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT si.*, b.name as building_name, b.area,
            cl.name as client_name, cl.short_name
        FROM scheduled_inspections si
        JOIN buildings b ON b.id = si.building_id
        JOIN clients cl ON cl.id = b.client_id
        WHERE si.status = 'scheduled'
        ORDER BY si.scheduled_date ASC
    """, conn)
    conn.close()
    return df


def is_building_scheduled(building_id):
    """Check if a building has a pending scheduled inspection."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM scheduled_inspections
        WHERE building_id = ? AND status = 'scheduled'
    """, (building_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


# ---------------------------------------------------------------------------
# FINANCIAL QUERIES
# ---------------------------------------------------------------------------

def get_financial_summary():
    """
    Return overall financial summary:
    total_contract_value, total_collected, total_outstanding, total_overdue
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(annual_value), 0) FROM contracts WHERE status = 'active'
    """)
    total_contract_value = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(p.amount), 0)
        FROM payments p
        JOIN contracts c ON c.id = p.contract_id
        WHERE p.status = 'received' AND c.status = 'active'
    """)
    total_collected = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(p.amount), 0)
        FROM payments p
        JOIN contracts c ON c.id = p.contract_id
        WHERE p.status = 'overdue' AND c.status = 'active'
    """)
    total_overdue = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM payments p
        JOIN contracts c ON c.id = p.contract_id
        WHERE p.status IN ('pending', 'overdue') AND c.status = 'active'
    """)
    outstanding_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM payments p
        JOIN contracts c ON c.id = p.contract_id
        WHERE p.status = 'overdue' AND c.status = 'active'
    """)
    overdue_count = cursor.fetchone()[0]

    total_outstanding = total_contract_value - total_collected

    conn.close()
    return {
        "total_contract_value": total_contract_value,
        "total_collected": total_collected,
        "total_outstanding": total_outstanding,
        "total_overdue": total_overdue,
        "outstanding_count": outstanding_count,
        "overdue_count": overdue_count,
        "collection_pct": (total_collected / total_contract_value * 100)
        if total_contract_value > 0 else 0,
    }


def get_client_financial_breakdown():
    """Return per-client financial breakdown."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            cl.name as "Client",
            COALESCE(SUM(DISTINCT c.annual_value), 0) as "Contract Value (AED)",
            COALESCE(
                (SELECT SUM(p.amount)
                 FROM payments p
                 JOIN contracts c2 ON c2.id = p.contract_id
                 JOIN buildings b2 ON b2.id = c2.building_id
                 WHERE b2.client_id = cl.id AND p.status = 'received' AND c2.status = 'active'),
                0
            ) as "Paid (AED)",
            COALESCE(SUM(DISTINCT c.annual_value), 0) -
            COALESCE(
                (SELECT SUM(p.amount)
                 FROM payments p
                 JOIN contracts c2 ON c2.id = p.contract_id
                 JOIN buildings b2 ON b2.id = c2.building_id
                 WHERE b2.client_id = cl.id AND p.status = 'received' AND c2.status = 'active'),
                0
            ) as "Outstanding (AED)",
            CASE
                WHEN COALESCE(
                    (SELECT SUM(p.amount)
                     FROM payments p
                     JOIN contracts c2 ON c2.id = p.contract_id
                     JOIN buildings b2 ON b2.id = c2.building_id
                     WHERE b2.client_id = cl.id AND p.status = 'received' AND c2.status = 'active'),
                    0
                ) >= COALESCE(SUM(DISTINCT c.annual_value), 0) THEN 'Fully Paid'
                WHEN EXISTS (
                    SELECT 1 FROM payments p
                    JOIN contracts c2 ON c2.id = p.contract_id
                    JOIN buildings b2 ON b2.id = c2.building_id
                    WHERE b2.client_id = cl.id AND p.status = 'overdue'
                ) THEN 'Payment Overdue'
                ELSE 'Partially Paid'
            END as "Status"
        FROM clients cl
        LEFT JOIN buildings b ON b.client_id = cl.id
        LEFT JOIN contracts c ON c.building_id = b.id AND c.status = 'active'
        GROUP BY cl.id
        ORDER BY "Contract Value (AED)" DESC
    """, conn)
    conn.close()
    return df


def get_payment_history(limit=20):
    """Return recent payment records."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            p.payment_date as "Date",
            cl.name as "Client",
            b.name as "Building",
            p.amount as "Amount (AED)",
            p.method as "Method",
            p.reference_number as "Reference",
            p.status as "Status"
        FROM payments p
        JOIN contracts c ON c.id = p.contract_id
        JOIN buildings b ON b.id = c.building_id
        JOIN clients cl ON cl.id = b.client_id
        ORDER BY p.payment_date DESC
        LIMIT ?
    """, conn, params=[limit])
    conn.close()
    return df


def get_monthly_revenue(months=6):
    """Return monthly revenue aggregation for the last N months."""
    cutoff = (date.today() - timedelta(days=months * 30)).isoformat()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            strftime('%Y-%m', p.payment_date) as month,
            SUM(p.amount) as total
        FROM payments p
        WHERE p.status = 'received' AND p.payment_date >= ?
        GROUP BY strftime('%Y-%m', p.payment_date)
        ORDER BY month ASC
    """, conn, params=[cutoff])
    conn.close()
    return df


def get_outstanding_invoices():
    """Return contracts with pending/overdue payments."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            cl.name as "Client",
            b.name as "Building",
            c.annual_value as "Contract Value (AED)",
            p.amount as "Amount Due (AED)",
            p.payment_date as "Due Date",
            CAST(julianday(?) - julianday(p.payment_date) AS INTEGER) as "Days Overdue",
            p.status as "Status"
        FROM payments p
        JOIN contracts c ON c.id = p.contract_id
        JOIN buildings b ON b.id = c.building_id
        JOIN clients cl ON cl.id = b.client_id
        WHERE p.status IN ('pending', 'overdue') AND c.status = 'active'
        ORDER BY p.payment_date ASC
    """, conn, params=[date.today().isoformat()])
    conn.close()
    return df


def get_client_financial_detail(client_id):
    """Return financial details for a specific client."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(c.annual_value), 0)
        FROM contracts c
        JOIN buildings b ON b.id = c.building_id
        WHERE b.client_id = ? AND c.status = 'active'
    """, (client_id,))
    total_value = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(p.amount), 0)
        FROM payments p
        JOIN contracts c ON c.id = p.contract_id
        JOIN buildings b ON b.id = c.building_id
        WHERE b.client_id = ? AND p.status = 'received' AND c.status = 'active'
    """, (client_id,))
    total_paid = cursor.fetchone()[0]

    conn.close()
    return {
        "total_value": total_value,
        "total_paid": total_paid,
        "outstanding": total_value - total_paid,
    }
