import { apiFetch, getSessionUser, clearSession, setSession } from './api.js';
import * as views from './views.js';

// Application State
let state = {
  view: 'dashboard',
  search: '',
  statusFilter: 'All',
  members: [],
  trainers: [],
  plans: [],
  liveOccupancy: [],
  peakHours: [],
  dailyReports: [],
  monthlyReports: [],
  notifications: [],
  memberProfile: null // For logged-in Member profile data
};

const NAV_ROLES = {
  Admin: [
    ['dashboard', 'Dashboard (Admin)'],
    ['members', 'Members (Admin)'],
    ['trainers', 'Trainers (Admin)'],
    ['plans', 'Plans (Admin)'],
    ['attendance', 'Attendance Station'],
    ['reports', 'Reports & Scheduler'],
    ['notifications', 'Expiry Alerts'],
    ['trainer_clients', 'My Clients (Trainer)'],
    ['member_dashboard', 'Welcome (Member)'],
    ['member_subscription', 'Subscription (Member)']
  ],
  Trainer: [
    ['trainer_clients', 'My Clients'],
    ['attendance', 'Attendance Station']
  ],
  Member: [
    ['member_dashboard', 'Welcome'],
    ['attendance', 'Live Gym Floor'],
    ['member_subscription', 'My Subscription'],
    ['notifications', 'Alerts Log']
  ]
};

async function loadData() {
  const user = getSessionUser();
  if (!user) return;

  if (user.role === 'Admin') {
    const [statsRes, membersRes, trainersRes, plansRes, occRes, dailyRes, monthlyRes, peakRes, alertsRes, profileRes] = await Promise.all([
      apiFetch('/dashboard'),
      apiFetch('/members'),
      apiFetch('/trainers'),
      apiFetch('/plans'),
      apiFetch('/attendance/current'),
      apiFetch('/reports/daily'),
      apiFetch('/reports/monthly'),
      apiFetch('/reports/peak-hours'),
      apiFetch('/alerts'),
      apiFetch('/members/1')
    ]);

    if (statsRes && statsRes.data) state.stats = statsRes.data;
    if (membersRes && membersRes.data) state.members = membersRes.data;
    if (trainersRes && trainersRes.data) state.trainers = trainersRes.data;
    if (plansRes && plansRes.data) state.plans = plansRes.data;
    if (occRes && occRes.data) state.liveOccupancy = occRes.data;
    if (dailyRes && dailyRes.data) state.dailyReports = dailyRes.data;
    if (monthlyRes && monthlyRes.data) state.monthlyReports = monthlyRes.data;
    if (peakRes && peakRes.data) state.peakHours = peakRes.data;
    if (alertsRes && alertsRes.data) state.notifications = alertsRes.data;
    if (profileRes && profileRes.data) state.memberProfile = profileRes.data;
  } else if (user.role === 'Trainer') {
    const [membersRes, trainersRes, occRes] = await Promise.all([
      apiFetch('/members'),
      apiFetch('/trainers'),
      apiFetch('/attendance/current')
    ]);
    if (membersRes && membersRes.data) state.members = membersRes.data;
    if (trainersRes && trainersRes.data) state.trainers = trainersRes.data;
    if (occRes && occRes.data) state.liveOccupancy = occRes.data;
  } else if (user.role === 'Member') {
    const [profileRes, occRes, plansRes, alertsRes] = await Promise.all([
      apiFetch(`/members/${user.referenceId}`),
      apiFetch('/attendance/current'),
      apiFetch('/plans'),
      apiFetch('/alerts')
    ]);
    if (profileRes && profileRes.data) state.memberProfile = profileRes.data;
    if (occRes && occRes.data) state.liveOccupancy = occRes.data;
    if (plansRes && plansRes.data) state.plans = plansRes.data;
    if (alertsRes && alertsRes.data) state.notifications = alertsRes.data.filter(n => n.member_id === user.referenceId);
  }
}

export async function render() {
  const app = document.getElementById('app');
  const user = getSessionUser();

  if (!user) {
    app.innerHTML = views.viewLogin();
    setupLoginListeners();
    return;
  }

  await loadData();
  const navItems = NAV_ROLES[user.role];
  
  // Make sure current view matches allowed role views
  if (!navItems.some(([viewKey]) => viewKey === state.view)) {
    state.view = navItems[0][0];
  }

  app.innerHTML = `
    <div id="app-shell" style="display:flex;width:100%;min-height:100vh;">
      ${views.viewSidebar(user, state.view, navItems)}
      <main id="main" style="flex:1;min-width:0;"></main>
    </div>
  `;

  renderMain();
  setupShellListeners();
}

function renderMain() {
  const main = document.getElementById('main');
  const user = getSessionUser();
  if (!user) return;

  let html = '';
  if (user.role === 'Admin') {
    if (state.view === 'dashboard') {
      html = views.viewAdminDashboard(state.stats, state.liveOccupancy, state.peakHours, handleCheckOut);
    } else if (state.view === 'members') {
      html = views.viewAdminMembers(state.members, state.plans, state.trainers, state.search, state.statusFilter);
    } else if (state.view === 'trainers') {
      html = views.viewAdminTrainers(state.trainers);
    } else if (state.view === 'plans') {
      html = views.viewAdminPlans(state.plans);
    } else if (state.view === 'attendance') {
      html = views.viewAdminAttendance(state.liveOccupancy, state.members, handleCheckIn, handleCheckOut);
    } else if (state.view === 'reports') {
      html = views.viewAdminReports(state.dailyReports, state.monthlyReports);
    } else if (state.view === 'notifications') {
      html = views.viewNotificationsList(state.notifications);
    } else if (state.view === 'trainer_clients') {
      html = views.viewTrainerMembers(state.members, state.plans, state.trainers, state.search, state.statusFilter, 1);
    } else if (state.view === 'member_dashboard') {
      html = views.viewMemberDashboard(state.memberProfile, state.liveOccupancy, handleCheckIn, handleCheckOut);
    } else if (state.view === 'member_subscription') {
      html = views.viewMemberSubscription(state.memberProfile, state.plans);
    }
  } else if (user.role === 'Trainer') {
    if (state.view === 'trainer_clients') {
      html = views.viewTrainerMembers(state.members, state.plans, state.trainers, state.search, state.statusFilter, user.referenceId);
    } else if (state.view === 'attendance') {
      html = views.viewAdminAttendance(state.liveOccupancy, state.members, handleCheckIn, handleCheckOut);
    }
  } else if (user.role === 'Member') {
    if (state.view === 'member_dashboard') {
      html = views.viewMemberDashboard(state.memberProfile, state.liveOccupancy, handleCheckIn, handleCheckOut);
    } else if (state.view === 'attendance') {
      html = views.viewLiveOccupancyPanel(state.liveOccupancy, handleCheckOut);
    } else if (state.view === 'member_subscription') {
      html = views.viewMemberSubscription(state.memberProfile, state.plans);
    } else if (state.view === 'notifications') {
      html = views.viewNotificationsList(state.notifications);
    }
  }

  main.innerHTML = html;
  setupViewListeners();
}

// Listener Initializers
function setupLoginListeners() {
  const form = document.getElementById('login-form');
  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const email = form.email.value.trim();
      const password = form.password.value;
      
      const res = await apiFetch('/auth/login', 'POST', { email, password });
      if (res && res.status === 'Success') {
        setSession(res.token, res.role, res.reference_id, email);
        state.view = 'dashboard';
        toast('🔓 Signed in successfully!');
        render();
      } else {
        toast(`Error: ${res ? res.error : 'Invalid credentials'}`);
      }
    });
  }
}

function setupShellListeners() {
  // Navigation items
  const navItems = document.querySelectorAll('.main-nav .navitem');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      state.view = item.getAttribute('data-view');
      state.search = '';
      state.statusFilter = 'All';
      renderMain();
      
      // Update active nav styling
      navItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
    });
  });

  // Logout Button
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      clearSession();
      toast('🔒 Logged out successfully.');
      render();
    });
  }
}

function setupViewListeners() {
  // Members search and filter
  const searchInput = document.getElementById('members-search');
  if (searchInput) {
    searchInput.addEventListener('input', e => {
      state.search = e.target.value;
      renderMain();
      // Keep focus after typing
      document.getElementById('members-search').focus();
      document.getElementById('members-search').setSelectionRange(state.search.length, state.search.length);
    });
  }

  const filterSelect = document.getElementById('members-filter');
  if (filterSelect) {
    filterSelect.addEventListener('change', e => {
      state.statusFilter = e.target.value;
      renderMain();
    });
  }

  // Refresh SQL inside occupancy table
  const refreshBtn = document.querySelector('.refresh-sql-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      render();
    });
  }

  // Manual Trigger Scheduler Run inside reports
  const schedulerBtn = document.querySelector('.trigger-scheduler-run-btn');
  if (schedulerBtn) {
    schedulerBtn.addEventListener('click', async () => {
      schedulerBtn.disabled = true;
      const res = await apiFetch('/scheduler/run', 'POST');
      if (res && res.status === 'Success') {
        toast(`📅 ${res.message}`);
        render();
      } else {
        toast(`Error: ${res ? res.error : 'Execution failed'}`);
        schedulerBtn.disabled = false;
      }
    });
  }

  // Quick Check-In select dropdown
  const quickCheckInBtn = document.getElementById('quick-checkin-btn');
  if (quickCheckInBtn) {
    quickCheckInBtn.addEventListener('click', async () => {
      const select = document.getElementById('quick-checkin-select');
      if (!select || !select.value) {
        toast('Please select a member first.');
        return;
      }
      await handleCheckIn(parseInt(select.value));
    });
  }

  // Event Delegation for dynamically loaded buttons
  const main = document.getElementById('main');
  main.onclick = async e => {
    const target = e.target;

    // Check-In Direct Buttons
    if (target.classList.contains('check-in-direct-btn')) {
      const memberId = parseInt(target.getAttribute('data-mem-id'));
      await handleCheckIn(memberId);
    }

    // Check-Out Direct Buttons
    if (target.classList.contains('check-out-direct-btn')) {
      const attId = parseInt(target.getAttribute('data-att-id'));
      const memberId = parseInt(target.getAttribute('data-mem-id'));
      await handleCheckOut(attId, memberId);
    }

    // Member self check-in / check-out
    if (target.classList.contains('check-in-self-btn')) {
      const memberId = parseInt(target.getAttribute('data-mem-id'));
      await handleCheckIn(memberId);
    }

    if (target.classList.contains('check-out-self-btn')) {
      const memberId = parseInt(target.getAttribute('data-mem-id'));
      await handleCheckOut(null, memberId);
    }

    // Modal launchers
    if (target.classList.contains('add-member-modal-btn')) {
      openAddMemberModal();
    }
    if (target.classList.contains('add-trainer-modal-btn')) {
      openAddTrainerModal();
    }
    if (target.classList.contains('add-plan-modal-btn')) {
      openAddPlanModal();
    }

    // Renewal modals
    if (target.classList.contains('renew-subscription-modal-btn')) {
      const memberId = parseInt(target.getAttribute('data-mem-id'));
      const planId = parseInt(target.getAttribute('data-plan-id'));
      openRenewSubscriptionModal(memberId, planId);
    }

    if (target.classList.contains('renew-self-plan-btn')) {
      const memberId = parseInt(target.getAttribute('data-mem-id'));
      const planId = parseInt(target.getAttribute('data-plan-id'));
      openRenewSubscriptionModal(memberId, planId);
    }
  };
}

// Business Action Handlers
async function handleCheckIn(memberId) {
  const res = await apiFetch('/attendance/check-in', 'POST', { member_id: memberId });
  if (res && res.status === 'Success') {
    toast(`⏱️ Member checked in successfully!`);
    render();
  } else {
    toast(`Check-In Failed: ${res ? res.error : 'Network error'}`);
  }
}

async function handleCheckOut(attendanceId, memberId) {
  const payload = {};
  if (attendanceId) payload.attendance_id = attendanceId;
  if (memberId) payload.member_id = memberId;

  const res = await apiFetch('/attendance/check-out', 'POST', payload);
  if (res && res.status === 'Success') {
    toast(`⏱️ Checked out successfully!`);
    render();
  } else {
    toast(`Check-out Failed: ${res ? res.error : 'Network error'}`);
  }
}

// Modal Handlers
function showModal(title, bodyHtml, onSubmit) {
  const old = document.getElementById('action-modal');
  if (old) old.remove();

  const overlay = document.createElement('div');
  overlay.id = 'action-modal';
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-head">
        <h3>${title}</h3>
        <button class="modal-close" type="button" id="modal-close-x">×</button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
    </div>
  `;
  document.body.appendChild(overlay);

  const form = overlay.querySelector('form');
  if (form) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      onSubmit(new FormData(form));
    });
  }

  const closeX = document.getElementById('modal-close-x');
  if (closeX) closeX.onclick = closeModal;
  
  const cancelBtn = overlay.querySelector('.modal-cancel-btn');
  if (cancelBtn) cancelBtn.onclick = closeModal;

  overlay.onclick = e => {
    if (e.target === overlay) closeModal();
  };
}

function closeModal() {
  const m = document.getElementById('action-modal');
  if (m) m.remove();
}

function toast(message) {
  const old = document.getElementById('action-toast');
  if (old) old.remove();

  const el = document.createElement('div');
  el.id = 'action-toast';
  el.className = 'toast';
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// Individual Form Modal Builders
function openAddMemberModal() {
  showModal('Register New Member (sp_RegisterMember)', `
    <form>
      <div class="form-grid">
        <div class="form-group"><label>Full Name *</label><input name="full_name" required placeholder="e.g. Youssef Ahmed"></div>
        <div class="form-group"><label>Phone Number *</label><input name="phone" required placeholder="e.g. 01000000000"></div>
        <div class="form-group"><label>Email Address</label><input name="email" type="email" placeholder="youssef@email.com"></div>
        <div class="form-group"><label>Subscription Plan *</label>
          <select name="plan_id" required>
            ${state.plans.map(p => `<option value="${p.plan_id}">${p.name} (${p.duration_months}M - ${p.price} EGP)</option>`).join('')}
          </select>
        </div>
        <div class="form-group"><label>Assigned Trainer</label>
          <select name="trainer_id">
            <option value="">No Trainer</option>
            ${state.trainers.map(t => `<option value="${t.trainer_id}">${t.full_name} (${t.specialization || 'Fitness'})</option>`).join('')}
          </select>
        </div>
        <div class="form-group"><label>Gender</label>
          <select name="gender"><option>Male</option><option>Female</option></select>
        </div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost modal-cancel-btn">Cancel</button>
        <button type="submit" class="btn">Execute Registration</button>
      </div>
    </form>
  `, async fd => {
    const payload = {
      full_name: fd.get('full_name').trim(),
      phone: fd.get('phone').trim(),
      email: fd.get('email').trim(),
      plan_id: parseInt(fd.get('plan_id')),
      trainer_id: fd.get('trainer_id') ? parseInt(fd.get('trainer_id')) : null,
      gender: fd.get('gender')
    };

    const res = await apiFetch('/members/register', 'POST', payload);
    if (res && res.status === 'Success') {
      closeModal();
      toast(`✨ Member registered! Expiry: ${res.data.end_date}`);
      render();
    } else {
      toast(`Registration Error: ${res ? res.error : 'Failed'}`);
    }
  });
}

function openAddTrainerModal() {
  showModal('Add Trainer', `
    <form>
      <div class="form-grid">
        <div class="form-group"><label>Full Name *</label><input name="full_name" required></div>
        <div class="form-group"><label>Specialization *</label><input name="specialization" required placeholder="e.g. Bodybuilding"></div>
        <div class="form-group"><label>Phone</label><input name="phone"></div>
        <div class="form-group"><label>Email</label><input name="email" type="email"></div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost modal-cancel-btn">Cancel</button>
        <button type="submit" class="btn">Add Trainer</button>
      </div>
    </form>
  `, async fd => {
    const payload = {
      full_name: fd.get('full_name').trim(),
      specialization: fd.get('specialization').trim(),
      phone: fd.get('phone').trim(),
      email: fd.get('email').trim()
    };
    const res = await apiFetch('/trainers', 'POST', payload);
    if (res && res.status === 'Success') {
      closeModal();
      toast('Trainer added successfully.');
      render();
    } else {
      toast(`Error: ${res ? res.error : 'Failed'}`);
    }
  });
}

function openAddPlanModal() {
  showModal('Add Plan', `
    <form>
      <div class="form-grid">
        <div class="form-group"><label>Plan Name *</label><input name="name" required></div>
        <div class="form-group"><label>Duration (Months) *</label><input name="duration_months" type="number" min="1" required value="1"></div>
        <div class="form-group"><label>Price (EGP) *</label><input name="price" type="number" min="0" required></div>
        <div class="form-group"><label>Description</label><input name="description" placeholder="Plan details"></div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost modal-cancel-btn">Cancel</button>
        <button type="submit" class="btn">Add Plan</button>
      </div>
    </form>
  `, async fd => {
    const payload = {
      name: fd.get('name').trim(),
      duration_months: parseInt(fd.get('duration_months')),
      price: parseFloat(fd.get('price')),
      description: fd.get('description').trim()
    };
    const res = await apiFetch('/plans', 'POST', payload);
    if (res && res.status === 'Success') {
      closeModal();
      toast('Plan created successfully.');
      render();
    } else {
      toast(`Error: ${res ? res.error : 'Failed'}`);
    }
  });
}

function openRenewSubscriptionModal(memberId, activePlanId) {
  showModal('Renew Subscription (sp_RenewSubscription)', `
    <form>
      <div style="font-size:13.5px;color:var(--chalk-dim);margin-bottom:16px;">
        Select renewal plan and trainer variables for Member ID <strong>#${memberId}</strong>.
      </div>
      <div class="form-grid">
        <input type="hidden" name="member_id" value="${memberId}">
        <div class="form-group"><label>Renewal Plan</label>
          <select name="plan_id" required>
            ${state.plans.map(p => `<option value="${p.plan_id}" ${p.plan_id === activePlanId ? 'selected' : ''}>${p.name} (${p.duration_months}M - ${p.price} EGP)</option>`).join('')}
          </select>
        </div>
        <div class="form-group"><label>Assigned Trainer</label>
          <select name="trainer_id">
            <option value="">Retain Current / No Trainer</option>
            ${state.trainers.map(t => `<option value="${t.trainer_id}">${t.full_name}</option>`).join('')}
          </select>
        </div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost modal-cancel-btn">Cancel</button>
        <button type="submit" class="btn">Execute sp_RenewSubscription</button>
      </div>
    </form>
  `, async fd => {
    const payload = {
      member_id: parseInt(fd.get('member_id')),
      plan_id: fd.get('plan_id') ? parseInt(fd.get('plan_id')) : null,
      trainer_id: fd.get('trainer_id') ? parseInt(fd.get('trainer_id')) : null
    };

    const res = await apiFetch('/subscriptions/renew', 'POST', payload);
    if (res && res.status === 'Success') {
      closeModal();
      toast(`✨ Subscription renewed successfully! New Expiry: ${res.data.end_date}`);
      render();
    } else {
      toast(`Renewal Failed: ${res ? res.error : 'Failed'}`);
    }
  });
}

// Global Auth Changed Event Listener
window.addEventListener('auth_changed', () => {
  render();
});

// Run Initial Render
render();
