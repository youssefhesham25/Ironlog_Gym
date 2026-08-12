-- ============================================================================
-- IRONLOG Gym Management System - Views, Triggers, and Procedural Rules
-- SQL Engine: SQLite / Relational DB Standard
-- Version: 1.0
-- ============================================================================

-- ============================================================================
-- 1. VIEWS FOR REPORTING AND DASHBOARDS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- View: vw_CurrentOccupancy
-- Returns all members currently inside the gym (checked in without check-out)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_CurrentOccupancy;
CREATE VIEW vw_CurrentOccupancy AS
SELECT 
    a.attendance_id,
    m.member_id,
    m.full_name,
    m.phone,
    m.membership_status,
    p.name AS plan_name,
    t.full_name AS trainer_name,
    a.check_in_date,
    a.check_in_time,
    CAST((JULIANDAY('now', 'localtime') - JULIANDAY(a.check_in_date || ' ' || a.check_in_time)) * 24 * 60 AS INTEGER) AS duration_minutes
FROM Attendance a
JOIN Members m ON a.member_id = m.member_id
LEFT JOIN Subscriptions s ON m.member_id = s.member_id AND s.status IN ('Active', 'Expiring Soon')
LEFT JOIN Plans p ON s.plan_id = p.plan_id
LEFT JOIN Trainers t ON s.trainer_id = t.trainer_id
WHERE a.status = 'Checked In' AND a.check_out_time IS NULL
ORDER BY a.check_in_time ASC;

-- ----------------------------------------------------------------------------
-- View: vw_DailyAttendance
-- Summary of gym visits per day
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_DailyAttendance;
CREATE VIEW vw_DailyAttendance AS
SELECT 
    check_in_date AS date,
    COUNT(attendance_id) AS total_visitors,
    COUNT(CASE WHEN check_out_time IS NULL THEN 1 END) AS currently_inside,
    COUNT(CASE WHEN check_out_time IS NOT NULL THEN 1 END) AS completed_visits
FROM Attendance
GROUP BY check_in_date
ORDER BY check_in_date DESC;

-- ----------------------------------------------------------------------------
-- View: vw_MonthlyAttendance
-- Monthly gym attendance statistics
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_MonthlyAttendance;
CREATE VIEW vw_MonthlyAttendance AS
SELECT 
    STRFTIME('%Y-%m', check_in_date) AS month,
    COUNT(attendance_id) AS total_visits,
    COUNT(DISTINCT member_id) AS unique_members_attending,
    ROUND(CAST(COUNT(attendance_id) AS REAL) / COUNT(DISTINCT check_in_date), 1) AS avg_daily_attendance
FROM Attendance
GROUP BY STRFTIME('%Y-%m', check_in_date)
ORDER BY month DESC;

-- ----------------------------------------------------------------------------
-- View: vw_PeakHours
-- Analyzes attendance distribution across time slots to identify peak hours
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_PeakHours;
CREATE VIEW vw_PeakHours AS
SELECT 
    CASE 
        WHEN STRFTIME('%H:%M', check_in_time) BETWEEN '08:00' AND '09:59' THEN '08:00 - 10:00'
        WHEN STRFTIME('%H:%M', check_in_time) BETWEEN '10:00' AND '11:59' THEN '10:00 - 12:00'
        WHEN STRFTIME('%H:%M', check_in_time) BETWEEN '12:00' AND '14:59' THEN '12:00 - 15:00'
        WHEN STRFTIME('%H:%M', check_in_time) BETWEEN '15:00' AND '16:59' THEN '15:00 - 17:00'
        WHEN STRFTIME('%H:%M', check_in_time) BETWEEN '17:00' AND '18:59' THEN '17:00 - 19:00'
        WHEN STRFTIME('%H:%M', check_in_time) BETWEEN '19:00' AND '20:59' THEN '19:00 - 21:00'
        ELSE '21:00 - 23:59'
    END AS time_slot,
    COUNT(attendance_id) AS total_check_ins,
    ROUND(AVG(
        CASE 
            WHEN check_out_time IS NOT NULL THEN 
                CAST((JULIANDAY(check_out_date || ' ' || check_out_time) - JULIANDAY(check_in_date || ' ' || check_in_time)) * 24 * 60 AS INTEGER)
            ELSE NULL 
        END
    ), 0) AS avg_duration_minutes
FROM Attendance
GROUP BY time_slot
ORDER BY total_check_ins DESC;

-- ----------------------------------------------------------------------------
-- View: vw_ExpiringSubscriptions
-- Lists all subscriptions expiring within 7 days or already expired
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_ExpiringSubscriptions;
CREATE VIEW vw_ExpiringSubscriptions AS
SELECT 
    s.subscription_id,
    m.member_id,
    m.full_name AS member_name,
    m.phone,
    m.email,
    p.name AS plan_name,
    t.full_name AS trainer_name,
    s.start_date,
    s.end_date,
    CAST(ROUND(JULIANDAY(s.end_date) - JULIANDAY(DATE('now'))) AS INTEGER) AS days_remaining,
    s.status AS subscription_status,
    m.membership_status
FROM Subscriptions s
JOIN Members m ON s.member_id = m.member_id
JOIN Plans p ON s.plan_id = p.plan_id
LEFT JOIN Trainers t ON s.trainer_id = t.trainer_id
WHERE s.end_date <= DATE('now', '+7 days')
ORDER BY days_remaining ASC;


-- ============================================================================
-- 2. TRIGGERS FOR AUTOMATED EXPIRY & BUSINESS RULE ENFORCEMENT
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Trigger: trg_GenerateExpiryAlerts
-- Generates alert entries in ExpiryAlerts when a subscription is created/updated
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_GenerateExpiryAlerts;
CREATE TRIGGER trg_GenerateExpiryAlerts
AFTER INSERT ON Subscriptions
BEGIN
    -- Alert for Expired
    INSERT INTO ExpiryAlerts (member_id, subscription_id, alert_type, days_left, message, alert_date)
    SELECT 
        NEW.member_id,
        NEW.subscription_id,
        'Expired',
        CAST(ROUND(JULIANDAY(NEW.end_date) - JULIANDAY(DATE('now'))) AS INTEGER),
        'Membership for member ID ' || NEW.member_id || ' has expired.',
        DATE('now')
    WHERE NEW.end_date < DATE('now');

    -- Alert for Urgent (<= 3 days)
    INSERT INTO ExpiryAlerts (member_id, subscription_id, alert_type, days_left, message, alert_date)
    SELECT 
        NEW.member_id,
        NEW.subscription_id,
        'Urgent',
        CAST(ROUND(JULIANDAY(NEW.end_date) - JULIANDAY(DATE('now'))) AS INTEGER),
        'Urgent: Subscription expires in ' || CAST(ROUND(JULIANDAY(NEW.end_date) - JULIANDAY(DATE('now'))) AS INTEGER) || ' days.',
        DATE('now')
    WHERE NEW.end_date >= DATE('now') AND NEW.end_date <= DATE('now', '+3 days');

    -- Alert for Warning (4 to 7 days)
    INSERT INTO ExpiryAlerts (member_id, subscription_id, alert_type, days_left, message, alert_date)
    SELECT 
        NEW.member_id,
        NEW.subscription_id,
        'Warning',
        CAST(ROUND(JULIANDAY(NEW.end_date) - JULIANDAY(DATE('now'))) AS INTEGER),
        'Warning: Subscription expires in ' || CAST(ROUND(JULIANDAY(NEW.end_date) - JULIANDAY(DATE('now'))) AS INTEGER) || ' days.',
        DATE('now')
    WHERE NEW.end_date > DATE('now', '+3 days') AND NEW.end_date <= DATE('now', '+7 days');
END;

-- ----------------------------------------------------------------------------
-- Trigger: trg_PreventDuplicateCheckIn
-- Prevents a member from checking in if they already have an active session
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_PreventDuplicateCheckIn;
CREATE TRIGGER trg_PreventDuplicateCheckIn
BEFORE INSERT ON Attendance
FOR EACH ROW
WHEN EXISTS (
    SELECT 1 FROM Attendance 
    WHERE member_id = NEW.member_id 
      AND status = 'Checked In' 
      AND check_out_time IS NULL
)
BEGIN
    SELECT RAISE(ABORT, 'Member already has an active check-in session.');
END;
