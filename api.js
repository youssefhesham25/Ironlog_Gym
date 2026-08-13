/**
 * Central API fetch client and authentication utility.
 * Features an automatic "Offline Client-Side Sandbox Mode" for GitHub Pages and local files.
 * Includes real login/registration with phone + national ID authentication.
 */

const API_BASE = window.location.origin + '/api';

// Detect if we should run in serverless sandbox mode (GitHub Pages or local file)
const IS_SANDBOX = window.location.hostname.endsWith('github.io') || window.location.protocol === 'file:';

// Default static mockup data to seed the sandbox
const DEFAULT_PLANS = [
  { plan_id: 1, name: "Basic Plan", duration_months: 1, price: 500, description: "Cardio and weights floor access." },
  { plan_id: 2, name: "Premium Plan", duration_months: 3, price: 1350, description: "Full gym floor access + 3 group classes." },
  { plan_id: 3, name: "VIP Yearly", duration_months: 12, price: 4500, description: "24/7 access + locker + private trainer." }
];

const DEFAULT_TRAINERS = [
  { trainer_id: 1, full_name: "Captain Ahmed", specialization: "Bodybuilding", phone: "01011112222", email: "ahmed.trainer@gmail.com", status: "Active", assigned_member_count: 2 },
  { trainer_id: 2, full_name: "Captain Sara", specialization: "Cardio & Yoga", phone: "01022223333", email: "sara.trainer@gmail.com", status: "Active", assigned_member_count: 1 }
];

const DEFAULT_MEMBERS = [
  { member_id: 1, full_name: "Youssef Ahmed", phone: "01000000001", email: "youssef@gmail.com", membership_status: "Active", plan_name: "Premium Plan", plan_id: 2, trainer_name: "Captain Ahmed", trainer_id: 1, start_date: "2026-08-01", end_date: "2026-11-01" },
  { member_id: 2, full_name: "Nour El-Din", phone: "01000000002", email: "nour@gmail.com", membership_status: "Expiring Soon", plan_name: "Basic Plan", plan_id: 1, trainer_name: "Captain Sara", trainer_id: 2, start_date: "2026-07-15", end_date: "2026-08-15" },
  { member_id: 3, full_name: "Sara Ibrahim", phone: "01000000003", email: "sara.i@gmail.com", membership_status: "Expired", plan_name: "Basic Plan", plan_id: 1, trainer_name: null, trainer_id: null, start_date: "2026-06-01", end_date: "2026-07-01" },
  { member_id: 4, full_name: "Mahmoud Farouk", phone: "01099998888", email: "mahmoud.f@gmail.com", membership_status: "Active", plan_name: "VIP Yearly", plan_id: 3, trainer_name: "Captain Ahmed", trainer_id: 1, start_date: "2026-08-01", end_date: "2027-08-01" },
  { member_id: 5, full_name: "Layla Mansour", phone: "01011223344", email: "layla.m@gmail.com", membership_status: "Active", plan_name: "Premium Plan", plan_id: 2, trainer_name: "Captain Sara", trainer_id: 2, start_date: "2026-08-05", end_date: "2026-11-05" },
  { member_id: 6, full_name: "Omar Khattab", phone: "01022334455", email: "omar.k@yahoo.com", membership_status: "Active", plan_name: "Basic Plan", plan_id: 1, trainer_name: null, trainer_id: null, start_date: "2026-08-10", end_date: "2026-09-10" },
  { member_id: 7, full_name: "Karim Zaki", phone: "01033445566", email: "karim.z@gmail.com", membership_status: "Active", plan_name: "Premium Plan", plan_id: 2, trainer_name: "Captain Ahmed", trainer_id: 1, start_date: "2026-08-02", end_date: "2026-11-02" },
  { member_id: 8, full_name: "Ahmed Hassan", phone: "01044556677", email: "ahmed.h@yahoo.com", membership_status: "Inactive", plan_name: "Basic Plan", plan_id: 1, trainer_name: null, trainer_id: null, start_date: "2026-05-01", end_date: "2026-06-01" },
  { member_id: 9, full_name: "Mohamed Ali", phone: "01055667788", email: "mohamed.ali@gmail.com", membership_status: "Active", plan_name: "VIP Yearly", plan_id: 3, trainer_name: null, trainer_id: null, start_date: "2026-08-01", end_date: "2027-08-01" },
  { member_id: 10, full_name: "Hana Selim", phone: "01066778899", email: "hana.s@gmail.com", membership_status: "Active", plan_name: "Premium Plan", plan_id: 2, trainer_name: "Captain Sara", trainer_id: 2, start_date: "2026-08-09", end_date: "2026-11-09" }
];

const DEFAULT_ATTENDANCE = [
  { attendance_id: 1, member_id: 1, full_name: "Youssef Ahmed", phone: "01000000001", plan_name: "Premium Plan", check_in_time: "01:25", duration_minutes: 45 },
  { attendance_id: 2, member_id: 4, full_name: "Mahmoud Farouk", phone: "01099998888", plan_name: "VIP Yearly", check_in_time: "02:10", duration_minutes: 20 },
  { attendance_id: 3, member_id: 5, full_name: "Layla Mansour", phone: "01011223344", plan_name: "Premium Plan", check_in_time: "02:22", duration_minutes: 15 },
  { attendance_id: 4, member_id: 6, full_name: "Omar Khattab", phone: "01022334455", plan_name: "Basic Plan", check_in_time: "02:30", duration_minutes: 5 }
];

const DEFAULT_ALERTS = [
  { alert_id: 1, member_id: 2, member_name: "Nour El-Din", message: "Warning: Subscription expires in 2 days.", alert_type: "Warning", alert_date: "2026-08-13" },
  { alert_id: 2, member_id: 3, member_name: "Sara Ibrahim", message: "Critical: Subscription has expired.", alert_type: "Expired", alert_date: "2026-08-12" }
];

// Default users for authentication (phone + national_id)
const DEFAULT_USERS = [
  { user_id: 1, full_name: "Admin Staff", phone: "01000000000", national_id: "30001011234567", email: "admin@gmail.com", gender: "Male", date_of_birth: "2000-01-01", role: "Admin", reference_id: null },
  { user_id: 2, full_name: "Captain Ahmed", phone: "01011112222", national_id: "29601151234567", email: "ahmed.trainer@gmail.com", gender: "Male", date_of_birth: "1996-01-15", role: "Trainer", reference_id: 1 },
  { user_id: 3, full_name: "Captain Sara", phone: "01022223333", national_id: "29803011234567", email: "sara.trainer@gmail.com", gender: "Female", date_of_birth: "1998-03-01", role: "Trainer", reference_id: 2 },
  { user_id: 4, full_name: "Youssef Ahmed", phone: "01000000001", national_id: "29805141234567", email: "youssef@gmail.com", gender: "Male", date_of_birth: "1998-05-14", role: "Member", reference_id: 1 },
  { user_id: 5, full_name: "Nour El-Din", phone: "01000000002", national_id: "29712301234567", email: "nour@gmail.com", gender: "Male", date_of_birth: "1997-12-30", role: "Member", reference_id: 2 },
  { user_id: 6, full_name: "Sara Ibrahim", phone: "01000000003", national_id: "30002101234567", email: "sara.i@gmail.com", gender: "Female", date_of_birth: "2000-02-10", role: "Member", reference_id: 3 },
  { user_id: 7, full_name: "Mahmoud Farouk", phone: "01099998888", national_id: "29604121234567", email: "mahmoud.f@gmail.com", gender: "Male", date_of_birth: "1996-04-12", role: "Member", reference_id: 4 },
  { user_id: 8, full_name: "Layla Mansour", phone: "01011223344", national_id: "29909251234567", email: "layla.m@gmail.com", gender: "Female", date_of_birth: "1999-09-25", role: "Member", reference_id: 5 },
  { user_id: 9, full_name: "Omar Khattab", phone: "01022334455", national_id: "29208051234567", email: "omar.k@yahoo.com", gender: "Male", date_of_birth: "1992-08-05", role: "Member", reference_id: 6 },
  { user_id: 10, full_name: "Karim Zaki", phone: "01033445566", national_id: "29303151234567", email: "karim.z@gmail.com", gender: "Male", date_of_birth: "1993-03-15", role: "Member", reference_id: 7 }
];

// Initialize sandbox database in localStorage if empty
if (IS_SANDBOX) {
  if (!localStorage.getItem('sandbox_plans')) localStorage.setItem('sandbox_plans', JSON.stringify(DEFAULT_PLANS));
  if (!localStorage.getItem('sandbox_trainers')) localStorage.setItem('sandbox_trainers', JSON.stringify(DEFAULT_TRAINERS));
  if (!localStorage.getItem('sandbox_members')) localStorage.setItem('sandbox_members', JSON.stringify(DEFAULT_MEMBERS));
  if (!localStorage.getItem('sandbox_attendance')) localStorage.setItem('sandbox_attendance', JSON.stringify(DEFAULT_ATTENDANCE));
  if (!localStorage.getItem('sandbox_alerts')) localStorage.setItem('sandbox_alerts', JSON.stringify(DEFAULT_ALERTS));
  if (!localStorage.getItem('sandbox_users')) localStorage.setItem('sandbox_users', JSON.stringify(DEFAULT_USERS));
}

// ============================================================================
// SESSION MANAGEMENT (Real - uses localStorage)
// ============================================================================

export function getToken() {
  return localStorage.getItem('ironlog_token');
}

export function setSession(token, role, referenceId, email, fullName) {
  localStorage.setItem('ironlog_token', token || 'session_active');
  localStorage.setItem('ironlog_role', role);
  localStorage.setItem('ironlog_reference_id', referenceId || '');
  localStorage.setItem('ironlog_email', email || '');
  localStorage.setItem('ironlog_fullname', fullName || '');
}

export function clearSession() {
  localStorage.removeItem('ironlog_token');
  localStorage.removeItem('ironlog_role');
  localStorage.removeItem('ironlog_reference_id');
  localStorage.removeItem('ironlog_email');
  localStorage.removeItem('ironlog_fullname');
}

export function getSessionUser() {
  const token = localStorage.getItem('ironlog_token');
  if (!token) return null;
  return {
    token,
    role: localStorage.getItem('ironlog_role') || 'Member',
    referenceId: parseInt(localStorage.getItem('ironlog_reference_id')) || null,
    email: localStorage.getItem('ironlog_email') || '',
    fullName: localStorage.getItem('ironlog_fullname') || ''
  };
}

// ============================================================================
// VALIDATION HELPERS (exported for use in app.js)
// ============================================================================

export function validatePhone(phone) {
  if (!phone) return "Phone number is required";
  if (!/^[0-9]{11}$/.test(phone)) return "Phone must be exactly 11 digits";
  return null;
}

export function validateNationalId(nid) {
  if (!nid) return "National ID is required";
  if (!/^[0-9]{14}$/.test(nid)) return "National ID must be exactly 14 digits";
  return null;
}

export function validateEmail(email) {
  if (!email) return "Email is required";
  if (!/@gmail\.com$/i.test(email) && !/@yahoo\.com$/i.test(email)) {
    return "Email must end with @gmail.com or @yahoo.com";
  }
  return null;
}

export function validateAge(dob) {
  if (!dob) return "Date of birth is required";
  const birth = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  if (age < 16) return "You must be at least 16 years old";
  return null;
}

// ============================================================================
// API FETCH
// ============================================================================

export async function apiFetch(endpoint, method = 'GET', body = null) {
  if (!IS_SANDBOX) {
    try {
      const headers = { 'Content-Type': 'application/json' };
      const token = getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const opts = { method, headers };
      if (body) opts.body = JSON.stringify(body);
      const res = await fetch(`${API_BASE}${endpoint}`, opts);
      const json = await res.json();
      return json;
    } catch (err) {
      console.warn("Server connection failed. Falling back to Sandbox Mode:", err);
    }
  }

  return handleSandboxRequest(endpoint, method, body);
}

// ============================================================================
// CLIENT-SIDE DATABASE ENGINE (Sandbox Mode)
// ============================================================================

function handleSandboxRequest(endpoint, method, body) {
  const getTable = (name) => JSON.parse(localStorage.getItem('sandbox_' + name));
  const saveTable = (name, data) => localStorage.setItem('sandbox_' + name, JSON.stringify(data));

  const plans = getTable('plans');
  const trainers = getTable('trainers');
  const members = getTable('members');
  const attendance = getTable('attendance');
  const alerts = getTable('alerts');
  const users = getTable('users');

  // ---- AUTH ROUTES ----
  if (method === 'POST' && endpoint === '/auth/login') {
    const phone = (body.phone || '').trim();
    const national_id = (body.national_id || '').trim();

    const phoneErr = validatePhone(phone);
    if (phoneErr) return { status: "Error", error: phoneErr };
    const nidErr = validateNationalId(national_id);
    if (nidErr) return { status: "Error", error: nidErr };

    const user = users.find(u => u.phone === phone && u.national_id === national_id);
    if (!user) {
      return { status: "Error", error: "Invalid credentials. Phone or National ID not found." };
    }
    return {
      status: "Success",
      token: "session_" + user.user_id,
      role: user.role,
      reference_id: user.reference_id,
      email: user.email,
      full_name: user.full_name
    };
  }

  if (method === 'POST' && endpoint === '/auth/register') {
    const full_name = (body.full_name || '').trim();
    const phone = (body.phone || '').trim();
    const national_id = (body.national_id || '').trim();
    const email = (body.email || '').trim();
    const gender = body.gender || 'Male';
    const dob = body.date_of_birth || '';
    const role = body.role || 'Member';

    if (!full_name) return { status: "Error", error: "Full name is required" };
    const phoneErr = validatePhone(phone);
    if (phoneErr) return { status: "Error", error: phoneErr };
    const nidErr = validateNationalId(national_id);
    if (nidErr) return { status: "Error", error: nidErr };
    const emailErr = validateEmail(email);
    if (emailErr) return { status: "Error", error: emailErr };
    const ageErr = validateAge(dob);
    if (ageErr) return { status: "Error", error: ageErr };

    if (users.find(u => u.phone === phone)) {
      return { status: "Error", error: "This phone number is already registered" };
    }
    if (users.find(u => u.national_id === national_id)) {
      return { status: "Error", error: "This National ID is already registered" };
    }
    if (users.find(u => u.email === email)) {
      return { status: "Error", error: "This email is already registered" };
    }

    let reference_id = null;
    if (role === 'Member') {
      const nextMemberId = members.length > 0 ? Math.max(...members.map(m => m.member_id)) + 1 : 1;
      reference_id = nextMemberId;
      const newMember = {
        member_id: nextMemberId,
        full_name, phone, email,
        membership_status: "Active",
        plan_name: "Basic Plan", plan_id: 1,
        trainer_name: null, trainer_id: null,
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      };
      members.push(newMember);
      saveTable('members', members);
    } else if (role === 'Trainer') {
      const nextTrainerId = trainers.length > 0 ? Math.max(...trainers.map(t => t.trainer_id)) + 1 : 1;
      reference_id = nextTrainerId;
      const newTrainer = {
        trainer_id: nextTrainerId,
        full_name, phone, email,
        specialization: "General Fitness",
        status: "Active", assigned_member_count: 0
      };
      trainers.push(newTrainer);
      saveTable('trainers', trainers);
    }

    const nextUserId = users.length > 0 ? Math.max(...users.map(u => u.user_id)) + 1 : 1;
    const newUser = {
      user_id: nextUserId, full_name, phone, national_id, email, gender,
      date_of_birth: dob, role, reference_id
    };
    users.push(newUser);
    saveTable('users', users);

    return {
      status: "Success",
      token: "session_" + nextUserId,
      role: newUser.role,
      reference_id: newUser.reference_id,
      email: newUser.email,
      full_name: newUser.full_name
    };
  }

  // ---- DATA ROUTES ----
  if (method === 'GET') {
    if (endpoint === '/dashboard') {
      return {
        status: "Success",
        data: {
          total_members: members.length,
          active_members: members.filter(m => m.membership_status === 'Active').length,
          inside_gym: attendance.length,
          today_check_ins: attendance.length + 2,
          total_trainers: trainers.length,
          expiring_soon: members.filter(m => m.membership_status === 'Expiring Soon').length,
          expired_members: members.filter(m => m.membership_status === 'Expired').length
        }
      };
    }
    if (endpoint === '/members') { return { status: "Success", data: members }; }
    if (endpoint.startsWith('/members/')) {
      const id = parseInt(endpoint.split('/').pop());
      const m = members.find(x => x.member_id === id);
      return { status: "Success", data: m || members[0] };
    }
    if (endpoint === '/trainers') { return { status: "Success", data: trainers }; }
    if (endpoint === '/plans') { return { status: "Success", data: plans }; }
    if (endpoint === '/attendance/current') { return { status: "Success", data: attendance }; }
    if (endpoint === '/alerts') { return { status: "Success", data: alerts }; }
    if (endpoint === '/reports/daily') {
      return { status: "Success", data: [
        { date: "2026-08-13", total_visitors: attendance.length + 2, currently_inside: attendance.length },
        { date: "2026-08-12", total_visitors: 12, currently_inside: 0 }
      ]};
    }
    if (endpoint === '/reports/monthly') {
      return { status: "Success", data: [{ month: "August 2026", total_visits: 45, avg_daily_attendance: 3.5 }]};
    }
    if (endpoint === '/reports/peak-hours') {
      return { status: "Success", data: [
        { time_slot: "18:00 - 20:00", total_check_ins: 15, avg_duration_minutes: 75 },
        { time_slot: "08:00 - 10:00", total_check_ins: 8, avg_duration_minutes: 60 }
      ]};
    }
  }

  if (method === 'POST') {
    if (endpoint === '/members/register') {
      const nextId = members.length > 0 ? Math.max(...members.map(m => m.member_id)) + 1 : 1;
      const plan = plans.find(p => p.plan_id === body.plan_id);
      const trainer = trainers.find(t => t.trainer_id === body.trainer_id);
      const newMember = {
        member_id: nextId, full_name: body.full_name, phone: body.phone, email: body.email,
        membership_status: "Active", plan_name: plan ? plan.name : "Basic Plan", plan_id: body.plan_id,
        trainer_name: trainer ? trainer.full_name : null, trainer_id: body.trainer_id || null,
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      };
      members.push(newMember);
      saveTable('members', members);
      return { status: "Success", data: newMember };
    }
    if (endpoint === '/subscriptions/renew') {
      const mIdx = members.findIndex(x => x.member_id === body.member_id);
      if (mIdx !== -1) {
        members[mIdx].membership_status = "Active";
        members[mIdx].end_date = new Date(Date.now() + 60 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        saveTable('members', members);
        return { status: "Success", data: members[mIdx] };
      }
    }
    if (endpoint === '/attendance/check-in') {
      const m = members.find(x => x.member_id === body.member_id);
      if (m) {
        if (attendance.some(a => a.member_id === body.member_id)) {
          return { status: "Error", error: "Member is already checked in." };
        }
        const newAtt = {
          attendance_id: Date.now(), member_id: m.member_id, full_name: m.full_name,
          phone: m.phone, plan_name: m.plan_name,
          check_in_time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
          duration_minutes: 0
        };
        attendance.push(newAtt);
        saveTable('attendance', attendance);
        return { status: "Success", data: newAtt };
      }
    }
    if (endpoint === '/attendance/check-out') {
      const attId = body.attendance_id;
      const memId = body.member_id;
      const index = attendance.findIndex(a => a.attendance_id === attId || a.member_id === memId);
      if (index !== -1) {
        attendance.splice(index, 1);
        saveTable('attendance', attendance);
        return { status: "Success" };
      }
    }
    if (endpoint === '/plans') {
      const nextId = plans.length > 0 ? Math.max(...plans.map(p => p.plan_id)) + 1 : 1;
      const newPlan = { plan_id: nextId, ...body };
      plans.push(newPlan);
      saveTable('plans', plans);
      return { status: "Success", plan_id: nextId };
    }
    if (endpoint === '/trainers') {
      const nextId = trainers.length > 0 ? Math.max(...trainers.map(t => t.trainer_id)) + 1 : 1;
      const newTrainer = { trainer_id: nextId, ...body, status: "Active", assigned_member_count: 0 };
      trainers.push(newTrainer);
      saveTable('trainers', trainers);
      return { status: "Success", trainer_id: nextId };
    }
    if (endpoint === '/scheduler/run') {
      return { status: "Success", message: "Sandbox scheduler completed check-ins check." };
    }
  }

  return { status: "Error", error: "Not found" };
}
