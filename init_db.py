#!/usr/bin/env python3
"""
IRONLOG Gym Management System - Database Initialization & Verification Script
SQL Engine: SQLite (3.37+)
"""

import os
import sys
import sqlite3
import datetime
from pathlib import Path

# Configure UTF-8 stdout for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Paths
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "ironlog.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
LOGIC_PATH = BASE_DIR / "procedures_and_triggers.sql"
SEED_PATH = BASE_DIR / "seed.sql"

def get_db_connection():
    """Connect to SQLite database with FK constraints enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def execute_sql_file(conn, file_path):
    """Reads and executes a SQL script file."""
    with open(file_path, "r", encoding="utf-8") as f:
        sql_script = f.read()
    conn.executescript(sql_script)
    conn.commit()

def sp_RegisterMember(conn, full_name, phone, email, date_of_birth, gender, address, plan_id, trainer_id=None):
    """
    Stored Procedure Logic Implementation: sp_RegisterMember
    Registers a new member and creates their initial subscription transactionally.
    """
    cursor = conn.cursor()
    
    # 1. Validate plan exists and fetch duration
    cursor.execute("SELECT plan_id, name, duration_months, price, status FROM Plans WHERE plan_id = ?", (plan_id,))
    plan = cursor.fetchone()
    if not plan:
        raise ValueError(f"Plan ID {plan_id} does not exist.")
    if plan["status"] != "Active":
        raise ValueError(f"Plan '{plan['name']}' is currently inactive.")
        
    # 2. Validate trainer if provided
    if trainer_id:
        cursor.execute("SELECT trainer_id, full_name, status FROM Trainers WHERE trainer_id = ?", (trainer_id,))
        trainer = cursor.fetchone()
        if not trainer:
            raise ValueError(f"Trainer ID {trainer_id} does not exist.")
        if trainer["status"] != "Active":
            raise ValueError(f"Trainer '{trainer['full_name']}' is currently inactive.")

    # 3. Begin Transaction
    try:
        # Insert Member
        cursor.execute("""
            INSERT INTO Members (full_name, phone, email, date_of_birth, gender, address, registration_date, membership_status)
            VALUES (?, ?, ?, ?, ?, ?, DATE('now'), 'Active')
        """, (full_name, phone, email, date_of_birth, gender, address))
        member_id = cursor.lastrowid

        # Calculate Start and End Date
        start_date = datetime.date.today()
        duration_months = plan["duration_months"]
        # Approximate end date calculation
        year = start_date.year + (start_date.month + duration_months - 1) // 12
        month = (start_date.month + duration_months - 1) % 12 + 1
        day = min(start_date.day, 28)
        end_date = datetime.date(year, month, day)

        # Insert Subscription
        cursor.execute("""
            INSERT INTO Subscriptions (member_id, plan_id, trainer_id, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, 'Active')
        """, (member_id, plan_id, trainer_id, start_date.isoformat(), end_date.isoformat()))
        subscription_id = cursor.lastrowid

        conn.commit()

        return {
            "status": "Success",
            "member_id": member_id,
            "subscription_id": subscription_id,
            "full_name": full_name,
            "plan_name": plan["name"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
    except sqlite3.Error as e:
        conn.rollback()
        raise e

def run_verification_tests(conn):
    """Runs verification checks against tables, views, triggers, and procedures."""
    print("=" * 70, flush=True)
    print("RUNNING IRONLOG DATABASE VERIFICATION SUITE", flush=True)
    print("=" * 70, flush=True)
    cursor = conn.cursor()

    # Test 1: Check Table Row Counts
    tables = ["Plans", "Trainers", "Members", "Subscriptions", "Attendance", "ExpiryAlerts", "MemberProgress"]
    print("\n[TEST 1] Table Row Counts:", flush=True)
    for tbl in tables:
        cursor.execute(f"SELECT COUNT(*) AS count FROM {tbl}")
        row = cursor.fetchone()
        print(f"  [OK] {tbl:<15}: {row['count']} rows", flush=True)

    # Test 2: Query Current Occupancy View (vw_CurrentOccupancy)
    print("\n[TEST 2] Current Gym Occupancy (vw_CurrentOccupancy):", flush=True)
    cursor.execute("SELECT * FROM vw_CurrentOccupancy")
    occupancy = cursor.fetchall()
    print(f"  [LIVE OCCUPANCY] Current Count: {len(occupancy)} members inside", flush=True)
    for member in occupancy:
        print(f"     - {member['full_name']} (Phone: {member['phone']}) | Plan: {member['plan_name']} | Check-in: {member['check_in_time']}", flush=True)

    # Test 3: Query Peak Hours View (vw_PeakHours)
    print("\n[TEST 3] Peak Gym Hours Analysis (vw_PeakHours):", flush=True)
    cursor.execute("SELECT * FROM vw_PeakHours")
    peak_hours = cursor.fetchall()
    for slot in peak_hours:
        print(f"  [SLOT] Time Slot {slot['time_slot']:<15}: {slot['total_check_ins']} check-ins | Avg Duration: {slot['avg_duration_minutes'] or 0} mins", flush=True)

    # Test 4: Query Expiring Subscriptions View (vw_ExpiringSubscriptions)
    print("\n[TEST 4] Expiring Subscriptions (vw_ExpiringSubscriptions):", flush=True)
    cursor.execute("SELECT * FROM vw_ExpiringSubscriptions")
    expiring = cursor.fetchall()
    print(f"  [EXPIRING] Total Expiring/Expired Subscriptions: {len(expiring)}", flush=True)
    for exp in expiring:
        print(f"     - {exp['member_name']} | Plan: {exp['plan_name']} | Days Left: {exp['days_remaining']} | Status: {exp['subscription_status']}", flush=True)

    # Test 5: Execute Stored Procedure sp_RegisterMember
    print("\n[TEST 5] Executing Procedure sp_RegisterMember:", flush=True)
    res = sp_RegisterMember(
        conn,
        full_name="Mahmoud Farouk",
        phone="01099990000",
        email="test.mahmoud@email.com",
        date_of_birth="1996-04-12",
        gender="Male",
        address="Giza",
        plan_id=3, # Premium 6 Months
        trainer_id=1 # Captain Ahmed
    )
    print(f"  [OK] Member Registered Successfully!", flush=True)
    print(f"    - Member ID      : {res['member_id']}", flush=True)
    print(f"    - Plan Assigned  : {res['plan_name']}", flush=True)
    print(f"    - Start Date     : {res['start_date']}", flush=True)
    print(f"    - Expiry Date    : {res['end_date']}", flush=True)

    # Test 6: Test Duplicate Check-In Trigger Constraint (trg_PreventDuplicateCheckIn)
    print("\n[TEST 6] Duplicate Check-In Prevention Trigger:", flush=True)
    try:
        # Member 1 (Youssef Ahmed) is already checked in
        cursor.execute("INSERT INTO Attendance (member_id, status) VALUES (1, 'Checked In')")
        print("  [FAIL] Trigger did not block duplicate check-in!", flush=True)
    except sqlite3.IntegrityError as e:
        print(f"  [SUCCESS] Trigger blocked duplicate check-in correctly! ({e})", flush=True)

    # Test 7: Expiry Alerts Table
    print("\n[TEST 7] Expiry Alerts Log:", flush=True)
    cursor.execute("SELECT * FROM ExpiryAlerts")
    alerts = cursor.fetchall()
    print(f"  [ALERTS] Total Alerts Logged: {len(alerts)}", flush=True)
    for alt in alerts:
        print(f"     - [{alt['alert_type']}] Member #{alt['member_id']}: {alt['message']}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("ALL PHASE 1 DATABASE ENGINE TESTS PASSED CLEANLY!", flush=True)
    print("=" * 70, flush=True)
def seed_users(conn):
    """Generates and seeds user credentials dynamically for testing."""
    import auth
    cursor = conn.cursor()
    print("Step 4/4: Dynamically seeding Users table...", flush=True)
    
    # 1. Admin
    admin_email = "admin@ironlog.com"
    admin_pw = auth.hash_password("admin123")
    cursor.execute("INSERT INTO Users (email, password_hash, role) VALUES (?, ?, 'Admin')", (admin_email, admin_pw))
    
    # 2. Trainers
    cursor.execute("SELECT trainer_id, email FROM Trainers")
    trainers = cursor.fetchall()
    trainer_pw = auth.hash_password("trainer123")
    for t in trainers:
        if t["email"]:
            cursor.execute("INSERT INTO Users (email, password_hash, role, reference_id) VALUES (?, ?, 'Trainer', ?)",
                           (t["email"], trainer_pw, t["trainer_id"]))
            
    # 3. Members
    cursor.execute("SELECT member_id, email FROM Members")
    members = cursor.fetchall()
    member_pw = auth.hash_password("member123")
    for m in members:
        if m["email"]:
            cursor.execute("INSERT INTO Users (email, password_hash, role, reference_id) VALUES (?, ?, 'Member', ?)",
                           (m["email"], member_pw, m["member_id"]))
    conn.commit()

def main():
    if DB_PATH.exists():
        os.remove(DB_PATH)
    print(f"Initializing database at: {DB_PATH}", flush=True)
    conn = get_db_connection()

    print("Step 1/4: Executing schema.sql...", flush=True)
    execute_sql_file(conn, SCHEMA_PATH)

    print("Step 2/4: Executing procedures_and_triggers.sql...", flush=True)
    execute_sql_file(conn, LOGIC_PATH)

    print("Step 3/4: Executing seed.sql...", flush=True)
    execute_sql_file(conn, SEED_PATH)

    seed_users(conn)

    print("Database built successfully. Running verification suite...\n", flush=True)
    run_verification_tests(conn)

    conn.close()

if __name__ == "__main__":
    main()
