#!/usr/bin/env python3
"""
IRONLOG Gym Management System - Database Service Layer
Version: 1.0
"""

import sqlite3
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "ironlog.db"

def get_db():
    """Connect to SQLite database with FK enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    """Converts sqlite3.Row to dictionary."""
    if row is None:
        return None
    return dict(row)

def list_from_rows(rows):
    """Converts list of sqlite3.Row to list of dictionaries."""
    return [dict(r) for r in rows]

# ============================================================================
# MEMBER OPERATIONS
# ============================================================================

def get_members(query=None, status=None, plan_id=None, trainer_id=None):
    """Retrieves list of members with optional filtering."""
    conn = get_db()
    cursor = conn.cursor()
    
    sql = """
        SELECT 
            m.member_id,
            m.full_name,
            m.phone,
            m.email,
            m.date_of_birth,
            m.gender,
            m.address,
            m.registration_date,
            m.membership_status,
            s.subscription_id,
            s.start_date,
            s.end_date,
            s.status AS subscription_status,
            p.name AS plan_name,
            p.plan_id,
            t.full_name AS trainer_name,
            t.trainer_id
        FROM Members m
        LEFT JOIN Subscriptions s ON m.member_id = s.member_id AND s.status IN ('Active', 'Expiring Soon')
        LEFT JOIN Plans p ON s.plan_id = p.plan_id
        LEFT JOIN Trainers t ON s.trainer_id = t.trainer_id
        WHERE 1=1
    """
    params = []
    
    if query:
        sql += " AND (m.full_name LIKE ? OR m.phone LIKE ? OR m.email LIKE ?)"
        pattern = f"%{query}%"
        params.extend([pattern, pattern, pattern])
        
    if status:
        sql += " AND m.membership_status = ?"
        params.append(status)
        
    if plan_id:
        sql += " AND s.plan_id = ?"
        params.append(plan_id)
        
    if trainer_id:
        sql += " AND s.trainer_id = ?"
        params.append(trainer_id)
        
    sql += " ORDER BY m.member_id DESC;"
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_member_by_id(member_id):
    """Retrieves detailed profile for a single member."""
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Member Basic Details & Active Subscription
    cursor.execute("""
        SELECT 
            m.*,
            s.subscription_id,
            s.start_date,
            s.end_date,
            s.status AS subscription_status,
            p.name AS plan_name,
            p.price AS plan_price,
            p.duration_months,
            t.full_name AS trainer_name,
            t.specialization AS trainer_specialization,
            (
                SELECT COUNT(*) FROM Attendance a WHERE a.member_id = m.member_id
            ) AS total_visits,
            (
                SELECT check_in_date FROM Attendance a WHERE a.member_id = m.member_id ORDER BY attendance_id DESC LIMIT 1
            ) AS last_visit_date,
            (
                SELECT status FROM Attendance a WHERE a.member_id = m.member_id AND check_out_time IS NULL LIMIT 1
            ) AS current_gym_status
        FROM Members m
        LEFT JOIN Subscriptions s ON m.member_id = s.member_id AND s.status IN ('Active', 'Expiring Soon')
        LEFT JOIN Plans p ON s.plan_id = p.plan_id
        LEFT JOIN Trainers t ON s.trainer_id = t.trainer_id
        WHERE m.member_id = ?
    """, (member_id,))
    member = cursor.fetchone()
    
    if not member:
        conn.close()
        return None
        
    member_dict = dict(member)
    
    # 2. Attendance History
    cursor.execute("""
        SELECT attendance_id, check_in_date, check_in_time, check_out_date, check_out_time, status
        FROM Attendance
        WHERE member_id = ?
        ORDER BY attendance_id DESC
        LIMIT 20;
    """, (member_id,))
    member_dict["attendance_history"] = list_from_rows(cursor.fetchall())
    
    # 3. Progress Logs
    cursor.execute("""
        SELECT progress_id, recorded_date, weight_kg, body_fat_pct, notes
        FROM MemberProgress
        WHERE member_id = ?
        ORDER BY recorded_date DESC;
    """, (member_id,))
    member_dict["progress_logs"] = list_from_rows(cursor.fetchall())
    
    conn.close()
    return member_dict

def register_member_sp(full_name, phone, email, date_of_birth, gender, address, plan_id, trainer_id=None):
    """Executes sp_RegisterMember procedure logic transactionally."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Validate plan
    cursor.execute("SELECT plan_id, name, duration_months, status FROM Plans WHERE plan_id = ?", (plan_id,))
    plan = cursor.fetchone()
    if not plan:
        conn.close()
        raise ValueError(f"Plan ID {plan_id} does not exist.")
    if plan["status"] != "Active":
        conn.close()
        raise ValueError(f"Plan '{plan['name']}' is currently inactive.")
        
    # Validate trainer
    if trainer_id:
        cursor.execute("SELECT trainer_id, full_name, status FROM Trainers WHERE trainer_id = ?", (trainer_id,))
        trainer = cursor.fetchone()
        if not trainer:
            conn.close()
            raise ValueError(f"Trainer ID {trainer_id} does not exist.")
            
    try:
        # Insert Member
        cursor.execute("""
            INSERT INTO Members (full_name, phone, email, date_of_birth, gender, address, registration_date, membership_status)
            VALUES (?, ?, ?, ?, ?, ?, DATE('now'), 'Active')
        """, (full_name, phone, email, date_of_birth, gender, address))
        member_id = cursor.lastrowid
        
        # Calculate End Date
        start_date = datetime.date.today()
        duration_months = plan["duration_months"]
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
        conn.close()
        
        return {
            "member_id": member_id,
            "subscription_id": subscription_id,
            "full_name": full_name,
            "plan_name": plan["name"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e

def renew_subscription_sp(member_id, plan_id=None, trainer_id=None):
    """Executes sp_RenewSubscription logic transactionally."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Find the member's most recent subscription
    cursor.execute("""
        SELECT subscription_id, plan_id, trainer_id, end_date, status
        FROM Subscriptions
        WHERE member_id = ?
        ORDER BY start_date DESC, subscription_id DESC
        LIMIT 1;
    """, (member_id,))
    current_sub = cursor.fetchone()

    if not current_sub:
        conn.close()
        raise ValueError(f"No existing subscription found for member ID {member_id}.")

    # Use existing plan and trainer if not provided
    if plan_id is None:
        plan_id = current_sub["plan_id"]
    if trainer_id is None:
        trainer_id = current_sub["trainer_id"]

    # 2. Validate plan
    cursor.execute("SELECT plan_id, name, duration_months, status FROM Plans WHERE plan_id = ?", (plan_id,))
    plan = cursor.fetchone()
    if not plan:
        conn.close()
        raise ValueError(f"Plan ID {plan_id} does not exist.")
    if plan["status"] != "Active":
        conn.close()
        raise ValueError(f"Plan '{plan['name']}' is currently inactive.")

    # Validate trainer
    if trainer_id:
        cursor.execute("SELECT trainer_id, full_name, status FROM Trainers WHERE trainer_id = ?", (trainer_id,))
        trainer = cursor.fetchone()
        if not trainer:
            conn.close()
            raise ValueError(f"Trainer ID {trainer_id} does not exist.")

    try:
        # 3. Determine start date
        today = datetime.date.today()
        current_end_date = datetime.datetime.strptime(current_sub["end_date"], "%Y-%m-%d").date()

        if current_end_date >= today:
            # extend from current expiry
            start_date = current_end_date + datetime.timedelta(days=1)
        else:
            # already expired: start today
            start_date = today

        # 4. Calculate new end date
        duration_months = plan["duration_months"]
        year = start_date.year + (start_date.month + duration_months - 1) // 12
        month = (start_date.month + duration_months - 1) % 12 + 1
        day = min(start_date.day, 28)
        end_date = datetime.date(year, month, day)

        # 5. Insert new subscription
        cursor.execute("""
            INSERT INTO Subscriptions (member_id, plan_id, trainer_id, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, 'Active')
        """, (member_id, plan_id, trainer_id, start_date.isoformat(), end_date.isoformat()))
        new_subscription_id = cursor.lastrowid

        # 6. Close out previous subscription
        cursor.execute("""
            UPDATE Subscriptions
            SET status = 'Expired'
            WHERE subscription_id = ?
        """, (current_sub["subscription_id"],))

        # 7. Update member status to Active
        cursor.execute("""
            UPDATE Members
            SET membership_status = 'Active'
            WHERE member_id = ?
        """, (member_id,))

        conn.commit()
        conn.close()

        return {
            "member_id": member_id,
            "subscription_id": new_subscription_id,
            "plan_name": plan["name"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e

def update_member(member_id, full_name, phone, email, address, gender):
    """Updates member personal details."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Members
        SET full_name = ?, phone = ?, email = ?, address = ?, gender = ?
        WHERE member_id = ?
    """, (full_name, phone, email, address, gender, member_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def set_member_status(member_id, status):
    """Updates member status."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Members SET membership_status = ? WHERE member_id = ?", (status, member_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ============================================================================
# ATTENDANCE OPERATIONS
# ============================================================================

def record_check_in(member_id):
    """Records member check-in with subscription validation."""
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Check member subscription status
    cursor.execute("""
        SELECT membership_status FROM Members WHERE member_id = ?
    """, (member_id,))
    member = cursor.fetchone()
    if not member:
        conn.close()
        raise ValueError(f"Member ID {member_id} does not exist.")
        
    if member["membership_status"] in ("Expired", "Inactive"):
        conn.close()
        raise ValueError(f"Check-in rejected: Member subscription is currently '{member['membership_status']}'.")
        
    # 2. Perform check-in (trigger trg_PreventDuplicateCheckIn enforces single active session)
    try:
        now_date = datetime.date.today().isoformat()
        now_time = datetime.datetime.now().strftime("%H:%M:%S")
        
        cursor.execute("""
            INSERT INTO Attendance (member_id, check_in_date, check_in_time, status)
            VALUES (?, ?, ?, 'Checked In')
        """, (member_id, now_date, now_time))
        
        attendance_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "attendance_id": attendance_id,
            "member_id": member_id,
            "check_in_date": now_date,
            "check_in_time": now_time,
            "status": "Checked In"
        }
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError("Member is already checked in to the gym.")

def record_check_out(attendance_id=None, member_id=None):
    """Records check-out for active attendance session."""
    conn = get_db()
    cursor = conn.cursor()
    
    now_date = datetime.date.today().isoformat()
    now_time = datetime.datetime.now().strftime("%H:%M:%S")
    
    if attendance_id:
        cursor.execute("""
            UPDATE Attendance
            SET check_out_date = ?, check_out_time = ?, status = 'Checked Out'
            WHERE attendance_id = ? AND status = 'Checked In'
        """, (now_date, now_time, attendance_id))
    elif member_id:
        cursor.execute("""
            UPDATE Attendance
            SET check_out_date = ?, check_out_time = ?, status = 'Checked Out'
            WHERE member_id = ? AND status = 'Checked In' AND check_out_time IS NULL
        """, (now_date, now_time, member_id))
    else:
        conn.close()
        raise ValueError("Must provide either attendance_id or member_id.")
        
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected == 0:
        raise ValueError("No active check-in session found to check out.")
    return True

def get_current_occupancy():
    """Retrieves active members inside the gym from vw_CurrentOccupancy."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vw_CurrentOccupancy;")
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_today_attendance():
    """Retrieves all check-in/out records for today."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            a.attendance_id,
            a.member_id,
            m.full_name,
            m.phone,
            a.check_in_date,
            a.check_in_time,
            a.check_out_date,
            a.check_out_time,
            a.status
        FROM Attendance a
        JOIN Members m ON a.member_id = m.member_id
        WHERE a.check_in_date = DATE('now')
        ORDER BY a.attendance_id DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)


# ============================================================================
# PLANS & TRAINERS OPERATIONS
# ============================================================================

def get_plans():
    """Retrieves all subscription plans."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Plans ORDER BY price ASC;")
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def create_plan(name, duration_months, price, description):
    """Creates a new plan."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Plans (name, duration_months, price, description, status)
        VALUES (?, ?, ?, ?, 'Active')
    """, (name, duration_months, price, description))
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id

def update_plan(plan_id, name, duration_months, price, description, status):
    """Updates an existing plan."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Plans
        SET name = ?, duration_months = ?, price = ?, description = ?, status = ?
        WHERE plan_id = ?
    """, (name, duration_months, price, description, status, plan_id))
    conn.commit()
    conn.close()
    return True

def get_trainers():
    """Retrieves all trainers with assigned member count."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            t.*,
            (
                SELECT COUNT(*) FROM Subscriptions s WHERE s.trainer_id = t.trainer_id AND s.status = 'Active'
            ) AS active_members_count
        FROM Trainers t
        ORDER BY t.trainer_id ASC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def create_trainer(full_name, phone, email, specialization):
    """Creates a new trainer."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Trainers (full_name, phone, email, specialization, hire_date, status)
        VALUES (?, ?, ?, ?, DATE('now'), 'Active')
    """, (full_name, phone, email, specialization))
    trainer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trainer_id

def update_trainer(trainer_id, full_name, phone, email, specialization, status):
    """Updates an existing trainer."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Trainers
        SET full_name = ?, phone = ?, email = ?, specialization = ?, status = ?
        WHERE trainer_id = ?
    """, (full_name, phone, email, specialization, status, trainer_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ============================================================================
# REPORTS & DASHBOARD ANALYTICS
# ============================================================================

def get_dashboard_stats():
    """Retrieves aggregated operational metrics for the main dashboard."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Member counts
    cursor.execute("SELECT COUNT(*) FROM Members;")
    total_members = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Members WHERE membership_status = 'Active';")
    active_members = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Members WHERE membership_status = 'Expiring Soon';")
    expiring_soon = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Members WHERE membership_status = 'Expired';")
    expired_members = cursor.fetchone()[0]
    
    # Gym Occupancy
    cursor.execute("SELECT COUNT(*) FROM Attendance WHERE status = 'Checked In' AND check_out_time IS NULL;")
    inside_gym = cursor.fetchone()[0]
    
    # Determine crowd level category
    if inside_gym <= 15:
        crowd_level = "Quiet"
        crowd_color = "Green"
    elif inside_gym <= 30:
        crowd_level = "Moderate"
        crowd_color = "Yellow"
    else:
        crowd_level = "Crowded"
        crowd_color = "Red"
        
    # Today's Check-ins Count
    cursor.execute("SELECT COUNT(*) FROM Attendance WHERE check_in_date = DATE('now');")
    today_check_ins = cursor.fetchone()[0]
    
    # Trainers Count
    cursor.execute("SELECT COUNT(*) FROM Trainers WHERE status = 'Active';")
    total_trainers = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_members": total_members,
        "active_members": active_members,
        "expiring_soon": expiring_soon,
        "expired_members": expired_members,
        "inside_gym": inside_gym,
        "crowd_level": crowd_level,
        "crowd_color": crowd_color,
        "today_check_ins": today_check_ins,
        "total_trainers": total_trainers
    }

def get_daily_report():
    """Queries vw_DailyAttendance."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vw_DailyAttendance LIMIT 30;")
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_monthly_report():
    """Queries vw_MonthlyAttendance."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vw_MonthlyAttendance;")
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_peak_hours_report():
    """Queries vw_PeakHours."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vw_PeakHours;")
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_alerts():
    """Queries ExpiryAlerts and vw_ExpiringSubscriptions."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            ea.alert_id,
            ea.member_id,
            m.full_name AS member_name,
            m.phone,
            ea.alert_type,
            ea.days_left,
            ea.message,
            ea.alert_date,
            ea.is_read
        FROM ExpiryAlerts ea
        JOIN Members m ON ea.member_id = m.member_id
        ORDER BY ea.is_read ASC, ea.days_left ASC, ea.alert_id DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def process_subscription_expiries():
    """
    Scans subscriptions, generates ExpiryAlerts for status changes,
    and updates Subscriptions/Members status as time passes.
    Runs transactionally.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # A. Transition to Expired: end_date < DATE('now')
        cursor.execute("""
            SELECT subscription_id, member_id
            FROM Subscriptions
            WHERE status IN ('Active', 'Expiring Soon') AND end_date < DATE('now')
        """)
        expired_subs = cursor.fetchall()
        for sub in expired_subs:
            sub_id = sub["subscription_id"]
            member_id = sub["member_id"]
            cursor.execute("UPDATE Subscriptions SET status = 'Expired' WHERE subscription_id = ?", (sub_id,))
            cursor.execute("UPDATE Members SET membership_status = 'Expired' WHERE member_id = ?", (member_id,))
            
            cursor.execute("SELECT 1 FROM ExpiryAlerts WHERE subscription_id = ? AND alert_type = 'Expired'", (sub_id,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO ExpiryAlerts (member_id, subscription_id, alert_type, days_left, message, alert_date)
                    VALUES (?, ?, 'Expired', -1, 'Membership for member ID ' || ? || ' has expired.', DATE('now'))
                """, (member_id, sub_id, member_id))
                
        # B. Transition to Expiring Soon (Urgent): end_date >= DATE('now') and end_date <= DATE('now', '+3 days')
        cursor.execute("""
            SELECT subscription_id, member_id, 
                   CAST(ROUND(JULIANDAY(end_date) - JULIANDAY(DATE('now'))) AS INTEGER) as days_left
            FROM Subscriptions
            WHERE status = 'Active' AND end_date >= DATE('now') AND end_date <= DATE('now', '+3 days')
        """)
        urgent_subs = cursor.fetchall()
        for sub in urgent_subs:
            sub_id = sub["subscription_id"]
            member_id = sub["member_id"]
            days_left = sub["days_left"]
            cursor.execute("UPDATE Subscriptions SET status = 'Expiring Soon' WHERE subscription_id = ?", (sub_id,))
            cursor.execute("UPDATE Members SET membership_status = 'Expiring Soon' WHERE member_id = ?", (member_id,))
            
            cursor.execute("SELECT 1 FROM ExpiryAlerts WHERE subscription_id = ? AND alert_type = 'Urgent'", (sub_id,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO ExpiryAlerts (member_id, subscription_id, alert_type, days_left, message, alert_date)
                    VALUES (?, ?, 'Urgent', ?, 'Urgent: Subscription expires in ' || ? || ' days.', DATE('now'))
                """, (member_id, sub_id, days_left, days_left))
                
        # C. Transition to Expiring Soon (Warning): end_date > DATE('now', '+3 days') and end_date <= DATE('now', '+7 days')
        cursor.execute("""
            SELECT subscription_id, member_id,
                   CAST(ROUND(JULIANDAY(end_date) - JULIANDAY(DATE('now'))) AS INTEGER) as days_left
            FROM Subscriptions
            WHERE status = 'Active' AND end_date > DATE('now', '+3 days') AND end_date <= DATE('now', '+7 days')
        """)
        warning_subs = cursor.fetchall()
        for sub in warning_subs:
            sub_id = sub["subscription_id"]
            member_id = sub["member_id"]
            days_left = sub["days_left"]
            cursor.execute("UPDATE Subscriptions SET status = 'Expiring Soon' WHERE subscription_id = ?", (sub_id,))
            cursor.execute("UPDATE Members SET membership_status = 'Expiring Soon' WHERE member_id = ?", (member_id,))
            
            cursor.execute("SELECT 1 FROM ExpiryAlerts WHERE subscription_id = ? AND alert_type = 'Warning'", (sub_id,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO ExpiryAlerts (member_id, subscription_id, alert_type, days_left, message, alert_date)
                    VALUES (?, ?, 'Warning', ?, 'Warning: Subscription expires in ' || ? || ' days.', DATE('now'))
                """, (member_id, sub_id, days_left, days_left))
                
        conn.commit()
        return len(expired_subs) + len(urgent_subs) + len(warning_subs)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_attendance_per_member():
    """Report 1: Total visits per member."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.member_id,
            m.full_name AS member_name,
            COUNT(a.attendance_id) AS total_visits
        FROM Members m
        LEFT JOIN Attendance a ON a.member_id = m.member_id
        GROUP BY m.member_id, m.full_name
        ORDER BY total_visits DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_weekly_attendance():
    """Report 3: Weekly gym attendance statistics."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            date(check_in_date, 'weekday 1', '-7 days') AS week_start,
            COUNT(*) AS total_visits
        FROM Attendance
        GROUP BY week_start
        ORDER BY week_start DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_most_active_members(top_n=10):
    """Report 5: Top N most active members."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.member_id,
            m.full_name AS member_name,
            COUNT(a.attendance_id) AS total_visits
        FROM Members m
        JOIN Attendance a ON a.member_id = m.member_id
        GROUP BY m.member_id, m.full_name
        ORDER BY total_visits DESC
        LIMIT ?;
    """, (top_n,))
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_low_attendance(threshold=4, days=30):
    """Report 6: Members with attendance lower than threshold in the last N days."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.member_id,
            m.full_name AS member_name,
            COUNT(a.attendance_id) AS visits_count
        FROM Members m
        LEFT JOIN Attendance a ON a.member_id = m.member_id AND a.check_in_date >= DATE('now', ?)
        GROUP BY m.member_id, m.full_name
        HAVING visits_count < ?
        ORDER BY visits_count ASC;
    """, (f"-{days} days", threshold))
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_inactive_members(days=14):
    """Report 7: Members who have not visited in last N days."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.member_id,
            m.full_name AS member_name,
            MAX(a.check_in_date) AS last_visit,
            CAST(ROUND(JULIANDAY(DATE('now')) - JULIANDAY(MAX(a.check_in_date))) AS INTEGER) AS days_inactive
        FROM Members m
        LEFT JOIN Attendance a ON a.member_id = m.member_id
        GROUP BY m.member_id, m.full_name
        HAVING last_visit IS NULL OR days_inactive >= ?
        ORDER BY days_inactive DESC;
    """, (days,))
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_average_visit_duration():
    """Report 8: Average visit duration overall and per member."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.member_id,
            m.full_name AS member_name,
            ROUND(AVG(
                (JULIANDAY(a.check_out_date || ' ' || a.check_out_time) - JULIANDAY(a.check_in_date || ' ' || a.check_in_time)) * 24 * 60
            ), 1) AS avg_duration_minutes,
            COUNT(a.attendance_id) AS completed_visits
        FROM Attendance a
        JOIN Members m ON m.member_id = a.member_id
        WHERE a.check_out_time IS NOT NULL
        GROUP BY m.member_id, m.full_name
        ORDER BY avg_duration_minutes DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_attendance_by_plan():
    """Report 9: Attendance count grouped by subscription plan."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.plan_id,
            p.name AS plan_name,
            COUNT(a.attendance_id) AS total_visits,
            COUNT(DISTINCT a.member_id) AS distinct_members_attended
        FROM Attendance a
        JOIN Subscriptions s ON s.member_id = a.member_id AND a.check_in_date BETWEEN s.start_date AND s.end_date
        JOIN Plans p ON p.plan_id = s.plan_id
        GROUP BY p.plan_id, p.name
        ORDER BY total_visits DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def get_attendance_by_trainer():
    """Report 10: Attendance by trainer assigned members."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            t.trainer_id,
            t.full_name AS trainer_name,
            COUNT(a.attendance_id) AS total_visits_by_assigned_members,
            COUNT(DISTINCT s.member_id) AS assigned_member_count
        FROM Trainers t
        LEFT JOIN Subscriptions s ON s.trainer_id = t.trainer_id AND s.status = 'Active'
        LEFT JOIN Attendance a ON a.member_id = s.member_id
        GROUP BY t.trainer_id, t.full_name
        ORDER BY total_visits_by_assigned_members DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return list_from_rows(rows)

def authenticate_user(email, password):
    """Verifies user credentials and returns user details if valid."""
    import auth
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, email, password_hash, role, reference_id
        FROM Users
        WHERE email = ?
    """, (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user and auth.verify_password(password, user["password_hash"]):
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "role": user["role"],
            "reference_id": user["reference_id"]
        }
    return None
