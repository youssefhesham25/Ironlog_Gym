/**
 * Central API fetch client and authentication utility.
 * Features an automatic "Offline Client-Side Sandbox Mode" for GitHub Pages and local files.
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
  { trainer_id: 1, full_name: "Captain Ahmed", specialization: "Bodybuilding", phone: "01011112222", email: "ahmed.trainer@ironlog.com", status: "Active", assigned_member_count: 2 },
  { trainer_id: 2, full_name: "Captain Sara", specialization: "Cardio & Yoga", phone: "01022223333", email: "sara.trainer@ironlog.com", status: "Active", assigned_member_count: 1 }
];

const DEFAULT_MEMBERS = [
  { member_id: 1, full_name: "Youssef Ahmed", phone: "01000000001", email: "youssef@email.com", membership_status: "Active", plan_name: "Premium Plan", plan_id: 2, trainer_name: "Captain Ahmed", trainer_id: 1, start_date: "2026-08-01", end_date: "2026-11-01" },
  { member_id: 2, full_name: "Nour El-Din", phone: "01000000002", email: "nour@email.com", membership_status: "Expiring Soon", plan_name: "Basic Plan", plan_id: 1, trainer_name: "Captain Sara", trainer_id: 2, start_date: "2026-07-15", end_date: "2026-08-15" },
  { member_id: 3, full_name: "Sara Ibrahim", phone: "01000000003", email: "sara.i@email.com", membership_status: "Expired", plan_name: "Basic Plan", plan_id: 1, trainer_name: null, trainer_id: null, start_date: "2026-06-01", end_date: "2026-07-01" }
];

const DEFAULT_ATTENDANCE = [
  { attendance_id: 1, member_id: 1, full_name: "Youssef Ahmed", phone: "01000000001", plan_name: "Premium Plan", check_in_time: "01:25", duration_minutes: 45 }
];

const DEFAULT_ALERTS = [
  { alert_id: 1, member_id: 2, member_name: "Nour El-Din", message: "Warning: Subscription expires in 2 days.", alert_type: "Warning", alert_date: "2026-08-13" },
  { alert_id: 2, member_id: 3, member_name: "Sara Ibrahim", message: "Critical: Subscription has expired.", alert_type: "Expired", alert_date: "2026-08-12" }
];

// Initialize sandbox database in localStorage if empty
if (IS_SANDBOX) {
  if (!localStorage.getItem('sandbox_plans')) localStorage.setItem('sandbox_plans', JSON.stringify(DEFAULT_PLANS));
  if (!localStorage.getItem('sandbox_trainers')) localStorage.setItem('sandbox_trainers', JSON.stringify(DEFAULT_TRAINERS));
  if (!localStorage.getItem('sandbox_members')) localStorage.setItem('sandbox_members', JSON.stringify(DEFAULT_MEMBERS));
  if (!localStorage.getItem('sandbox_attendance')) localStorage.setItem('sandbox_attendance', JSON.stringify(DEFAULT_ATTENDANCE));
  if (!localStorage.getItem('sandbox_alerts')) localStorage.setItem('sandbox_alerts', JSON.stringify(DEFAULT_ALERTS));
}

export function getToken() {
  return 'mock_token';
}

export function setSession(token, role, referenceId, email) {
  // Bypassed
}

export function clearSession() {
  // Bypassed
}

export function getSessionUser() {
  return {
    token: 'mock_token',
    role: 'Admin',
    referenceId: null,
    email: 'admin@ironlog.com'
  };
}

export async function apiFetch(endpoint, method = 'GET', body = null) {
  if (!IS_SANDBOX) {
    // Normal backend integration
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

  // RUNNING IN SANDBOX MODE (GitHub Pages or local file)
  return handleSandboxRequest(endpoint, method, body);
}

// Client-Side Database Engine simulation for Sandbox Mode
function handleSandboxRequest(endpoint, method, body) {
  // Helper to fetch/save database tables from localStorage
  const getTable = (name) => JSON.parse(localStorage.getItem('sandbox_' + name));
  const saveTable = (name, data) => localStorage.setItem('sandbox_' + name, JSON.stringify(data));

  const plans = getTable('plans');
  const trainers = getTable('trainers');
  const members = getTable('members');
  const attendance = getTable('attendance');
  const alerts = getTable('alerts');

  // Route Handlers
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
    
    if (endpoint === '/members') {
      return { status: "Success", data: members };
    }
    
    if (endpoint.startsWith('/members/')) {
      const id = parseInt(endpoint.split('/').pop());
      const m = members.find(x => x.member_id === id);
      return { status: "Success", data: m || members[0] };
    }
    
    if (endpoint === '/trainers') {
      return { status: "Success", data: trainers };
    }
    
    if (endpoint === '/plans') {
      return { status: "Success", data: plans };
    }
    
    if (endpoint === '/attendance/current') {
      return { status: "Success", data: attendance };
    }

    if (endpoint === '/alerts') {
      return { status: "Success", data: alerts };
    }

    // Reports
    if (endpoint === '/reports/daily') {
      return {
        status: "Success",
        data: [
          { date: "2026-08-13", total_visitors: attendance.length + 2, currently_inside: attendance.length },
          { date: "2026-08-12", total_visitors: 12, currently_inside: 0 }
        ]
      };
    }

    if (endpoint === '/reports/monthly') {
      return {
        status: "Success",
        data: [
          { month: "August 2026", total_visits: 45, avg_daily_attendance: 3.5 }
        ]
      };
    }

    if (endpoint === '/reports/peak-hours') {
      return {
        status: "Success",
        data: [
          { time_slot: "18:00 - 20:00", total_check_ins: 15, avg_duration_minutes: 75 },
          { time_slot: "08:00 - 10:00", total_check_ins: 8, avg_duration_minutes: 60 }
        ]
      };
    }
  }

  if (method === 'POST') {
    if (endpoint === '/members/register') {
      const nextId = members.length > 0 ? Math.max(...members.map(m => m.member_id)) + 1 : 1;
      const plan = plans.find(p => p.plan_id === body.plan_id);
      const trainer = trainers.find(t => t.trainer_id === body.trainer_id);
      
      const newMember = {
        member_id: nextId,
        full_name: body.full_name,
        phone: body.phone,
        email: body.email,
        membership_status: "Active",
        plan_name: plan ? plan.name : "Basic Plan",
        plan_id: body.plan_id,
        trainer_name: trainer ? trainer.full_name : null,
        trainer_id: body.trainer_id || null,
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
        // Prevent duplicate check-in
        if (attendance.some(a => a.member_id === body.member_id)) {
          return { status: "Error", error: "Member is already checked in." };
        }
        const newAtt = {
          attendance_id: Date.now(),
          member_id: m.member_id,
          full_name: m.full_name,
          phone: m.phone,
          plan_name: m.plan_name,
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
