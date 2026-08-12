-- ============================================================================
-- IRONLOG Gym Management System - Seed Data
-- SQL Engine: SQLite / Relational DB Standard
-- Version: 1.0
-- ============================================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Clean existing data
DELETE FROM MemberProgress;
DELETE FROM ExpiryAlerts;
DELETE FROM Attendance;
DELETE FROM Subscriptions;
DELETE FROM Members;
DELETE FROM Trainers;
DELETE FROM Plans;

-- ----------------------------------------------------------------------------
-- 1. SEED PLANS
-- ----------------------------------------------------------------------------
INSERT INTO Plans (plan_id, name, duration_months, price, description, status) VALUES
(1, 'Basic', 1, 500.0, '1 Month standard access to gym floor and locker room.', 'Active'),
(2, 'Standard', 3, 1300.0, '3 Months access + 1 complimentary trainer consultation.', 'Active'),
(3, 'Premium', 6, 2400.0, '6 Months full access + sauna + dedicated locker.', 'Active'),
(4, 'Annual', 12, 4000.0, '12 Months VIP access + custom workout plan + priority trainer support.', 'Active');

-- ----------------------------------------------------------------------------
-- 2. SEED TRAINERS
-- ----------------------------------------------------------------------------
INSERT INTO Trainers (trainer_id, full_name, phone, email, specialization, hire_date, status) VALUES
(1, 'Ahmed Mohamed', '01011112222', 'ahmed.trainer@ironlog.com', 'Bodybuilding & Heavy Lifting', '2024-01-15', 'Active'),
(2, 'Sara Mahmoud', '01133334444', 'sara.trainer@ironlog.com', 'CrossFit & HIIT Conditioning', '2024-03-01', 'Active'),
(3, 'Hassan Tarek', '01255556666', 'hassan.trainer@ironlog.com', 'Cardio & Fat Loss', '2024-05-10', 'Active'),
(4, 'Mina Nabil', '01577778888', 'mina.trainer@ironlog.com', 'Functional Training & Mobility', '2024-06-20', 'Active');

-- ----------------------------------------------------------------------------
-- 3. SEED MEMBERS
-- ----------------------------------------------------------------------------
INSERT INTO Members (member_id, full_name, phone, email, date_of_birth, gender, address, registration_date, membership_status) VALUES
(1, 'Youssef Ahmed', '01000000001', 'youssef@email.com', '1998-05-14', 'Male', 'Maadi, Cairo', '2026-08-01', 'Active'),
(2, 'Ahmed Hassan', '01000000002', 'ahmed.h@email.com', '1995-11-20', 'Male', 'Nasr City, Cairo', '2026-07-15', 'Active'),
(3, 'Sara Ibrahim', '01000000003', 'sara.i@email.com', '2000-02-10', 'Female', 'Heliopolis, Cairo', '2026-05-12', 'Expiring Soon'),
(4, 'Omar Khaled', '01000000004', 'omar.k@email.com', '1992-08-05', 'Male', 'Zamalek, Cairo', '2026-06-01', 'Expired'),
(5, 'Layla Mahmoud', '01000000005', 'layla.m@email.com', '1999-09-25', 'Female', '5th Settlement, New Cairo', '2026-08-05', 'Active'),
(6, 'Mohamed Ali', '01000000006', 'mohamed.ali@email.com', '1994-04-18', 'Male', 'Dokki, Giza', '2026-07-01', 'Active'),
(7, 'Nour El-Din', '01000000007', 'nour@email.com', '1997-12-30', 'Male', 'Sheikh Zayed, Giza', '2026-08-02', 'Active'),
(8, 'Karim Zaki', '01000000008', 'karim.z@email.com', '1993-03-15', 'Male', 'Rehab City, New Cairo', '2026-07-20', 'Active');

-- ----------------------------------------------------------------------------
-- 4. SEED SUBSCRIPTIONS
-- ----------------------------------------------------------------------------
-- Active Subscriptions
INSERT INTO Subscriptions (subscription_id, member_id, plan_id, trainer_id, start_date, end_date, status) VALUES
(1, 1, 3, 1, '2026-08-01', '2027-02-01', 'Active'),
(2, 2, 2, 2, '2026-07-15', '2026-10-15', 'Active'),
(3, 5, 1, 3, '2026-08-05', '2026-09-05', 'Active'),
(4, 6, 4, 1, '2026-07-01', '2027-07-01', 'Active'),
(5, 7, 2, 4, '2026-08-02', '2026-11-02', 'Active'),
(6, 8, 3, 2, '2026-07-20', '2027-01-20', 'Active');

-- Expiring Soon Subscriptions (Within 7 Days)
INSERT INTO Subscriptions (subscription_id, member_id, plan_id, trainer_id, start_date, end_date, status) VALUES
(7, 3, 2, 3, '2026-05-12', DATE('now', '+3 days'), 'Expiring Soon');

-- Expired Subscriptions
INSERT INTO Subscriptions (subscription_id, member_id, plan_id, trainer_id, start_date, end_date, status) VALUES
(8, 4, 1, 4, '2026-06-01', '2026-07-01', 'Expired');

-- ----------------------------------------------------------------------------
-- 5. SEED ATTENDANCE HISTORY (Completed & Current Sessions)
-- ----------------------------------------------------------------------------
-- Historical completed visits (for peak hours & monthly reports)
INSERT INTO Attendance (member_id, check_in_date, check_in_time, check_out_date, check_out_time, status) VALUES
-- Yesterday's visits
(1, DATE('now', '-1 day'), '08:30:00', DATE('now', '-1 day'), '10:00:00', 'Checked Out'),
(2, DATE('now', '-1 day'), '17:30:00', DATE('now', '-1 day'), '19:15:00', 'Checked Out'),
(3, DATE('now', '-1 day'), '18:00:00', DATE('now', '-1 day'), '19:30:00', 'Checked Out'),
(6, DATE('now', '-1 day'), '18:15:00', DATE('now', '-1 day'), '20:00:00', 'Checked Out'),
(7, DATE('now', '-1 day'), '19:00:00', DATE('now', '-1 day'), '20:30:00', 'Checked Out'),

-- Past week visits
(1, DATE('now', '-3 days'), '17:45:00', DATE('now', '-3 days'), '19:15:00', 'Checked Out'),
(2, DATE('now', '-3 days'), '18:10:00', DATE('now', '-3 days'), '19:40:00', 'Checked Out'),
(5, DATE('now', '-3 days'), '10:15:00', DATE('now', '-3 days'), '11:45:00', 'Checked Out'),
(8, DATE('now', '-4 days'), '19:30:00', DATE('now', '-4 days'), '21:00:00', 'Checked Out'),
(6, DATE('now', '-5 days'), '17:30:00', DATE('now', '-5 days'), '19:00:00', 'Checked Out'),

-- Today's Completed Visits
(6, DATE('now'), '09:00:00', DATE('now'), '10:30:00', 'Checked Out'),
(7, DATE('now'), '11:00:00', DATE('now'), '12:30:00', 'Checked Out');

-- Currently Active Check-Ins (Members inside the gym right now)
INSERT INTO Attendance (member_id, check_in_date, check_in_time, check_out_date, check_out_time, status) VALUES
(1, DATE('now'), '17:30:00', NULL, NULL, 'Checked In'),
(2, DATE('now'), '18:10:00', NULL, NULL, 'Checked In'),
(5, DATE('now'), '18:45:00', NULL, NULL, 'Checked In');

-- ----------------------------------------------------------------------------
-- 6. SEED MEMBER PROGRESS
-- ----------------------------------------------------------------------------
INSERT INTO MemberProgress (member_id, recorded_date, weight_kg, body_fat_pct, notes) VALUES
(1, '2026-08-01', 82.5, 18.5, 'Initial assessment. Focus on hyperthrophy.'),
(1, '2026-08-08', 81.8, 17.9, 'Good strength progress in bench press.'),
(2, '2026-07-15', 90.0, 22.0, 'Starting weight loss cycle.'),
(2, '2026-08-01', 87.5, 20.2, 'Down 2.5kg! Endurance improving.'),
(5, '2026-08-05', 62.0, 24.0, 'HIIT conditioning baseline.');
