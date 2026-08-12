-- ============================================================================
-- IRONLOG Gym Management System - Database Schema
-- SQL Engine: SQLite / Relational DB Standard
-- Version: 1.0
-- ============================================================================

PRAGMA foreign_keys = ON;

-- Drop existing views if any
DROP VIEW IF EXISTS vw_ExpiringSubscriptions;
DROP VIEW IF EXISTS vw_PeakHours;
DROP VIEW IF EXISTS vw_MonthlyAttendance;
DROP VIEW IF EXISTS vw_DailyAttendance;
DROP VIEW IF EXISTS vw_CurrentOccupancy;

-- Drop existing tables in reverse dependency order
DROP TABLE IF EXISTS Users;
DROP TABLE IF EXISTS MemberProgress;
DROP TABLE IF EXISTS ExpiryAlerts;
DROP TABLE IF EXISTS Attendance;
DROP TABLE IF EXISTS Subscriptions;
DROP TABLE IF EXISTS Members;
DROP TABLE IF EXISTS Trainers;
DROP TABLE IF EXISTS Plans;

-- ----------------------------------------------------------------------------
-- 1. Plans Table: Stores available subscription plans
-- ----------------------------------------------------------------------------
CREATE TABLE Plans (
    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    duration_months INTEGER NOT NULL CHECK (duration_months > 0),
    price REAL NOT NULL CHECK (price >= 0),
    description TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Inactive')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 2. Trainers Table: Stores trainer profiles
-- ----------------------------------------------------------------------------
CREATE TABLE Trainers (
    trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT UNIQUE,
    email TEXT UNIQUE,
    specialization TEXT,
    hire_date DATE NOT NULL DEFAULT (DATE('now')),
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Inactive')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 3. Members Table: Stores gym member records
-- ----------------------------------------------------------------------------
CREATE TABLE Members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    date_of_birth DATE,
    gender TEXT CHECK (gender IN ('Male', 'Female', 'Other')),
    address TEXT,
    registration_date DATE NOT NULL DEFAULT (DATE('now')),
    membership_status TEXT NOT NULL DEFAULT 'Active' CHECK (membership_status IN ('Active', 'Expiring Soon', 'Expired', 'Inactive')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 4. Subscriptions Table: Stores membership subscriptions
-- ----------------------------------------------------------------------------
CREATE TABLE Subscriptions (
    subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES Members(member_id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES Plans(plan_id) ON DELETE RESTRICT,
    trainer_id INTEGER REFERENCES Trainers(trainer_id) ON DELETE SET NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Expiring Soon', 'Expired', 'Cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CHECK (start_date <= end_date)
);

-- ----------------------------------------------------------------------------
-- 5. Attendance Table: Records gym visits and check-in/out timestamps
-- ----------------------------------------------------------------------------
CREATE TABLE Attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES Members(member_id) ON DELETE CASCADE,
    check_in_date DATE NOT NULL DEFAULT (DATE('now')),
    check_in_time TEXT NOT NULL DEFAULT (TIME('now', 'localtime')),
    check_out_date DATE,
    check_out_time TEXT,
    status TEXT NOT NULL DEFAULT 'Checked In' CHECK (status IN ('Checked In', 'Checked Out')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 6. ExpiryAlerts Table: Stores automatically generated subscription alerts
-- ----------------------------------------------------------------------------
CREATE TABLE ExpiryAlerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES Members(member_id) ON DELETE CASCADE,
    subscription_id INTEGER NOT NULL REFERENCES Subscriptions(subscription_id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('Warning', 'Urgent', 'Expired')),
    days_left INTEGER NOT NULL,
    message TEXT NOT NULL,
    alert_date DATE NOT NULL DEFAULT (DATE('now')),
    is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 7. MemberProgress Table: Tracks weight and body composition metrics
-- ----------------------------------------------------------------------------
CREATE TABLE MemberProgress (
    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES Members(member_id) ON DELETE CASCADE,
    recorded_date DATE NOT NULL DEFAULT (DATE('now')),
    weight_kg REAL CHECK (weight_kg > 0),
    body_fat_pct REAL CHECK (body_fat_pct >= 0 AND body_fat_pct <= 100),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 8. Users Table: Centralized authentication table
-- ----------------------------------------------------------------------------
CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Admin', 'Trainer', 'Member')),
    reference_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION
-- ============================================================================
CREATE INDEX idx_users_email ON Users(email);
-- ============================================================================
CREATE INDEX idx_members_phone ON Members(phone);
CREATE INDEX idx_members_status ON Members(membership_status);
CREATE INDEX idx_subscriptions_member ON Subscriptions(member_id);
CREATE INDEX idx_subscriptions_status ON Subscriptions(status, end_date);
CREATE INDEX idx_attendance_member ON Attendance(member_id);
CREATE INDEX idx_attendance_active ON Attendance(status, check_in_date);
CREATE INDEX idx_alerts_member ON ExpiryAlerts(member_id, is_read);
