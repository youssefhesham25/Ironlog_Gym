import { apiFetch, getSessionUser, clearSession } from './api.js';

// Helpers
function memberName(members, id) {
  const m = members.find(x => x.member_id === id);
  return m ? m.full_name : 'Member #' + id;
}

function subStatusBadge(status) {
  if (status === 'Expired') return '<span class="badge expired">Expired</span>';
  if (status === 'Expiring Soon') return '<span class="badge expiring">Expiring soon</span>';
  if (status === 'Inactive') return '<span class="badge inactive">Inactive</span>';
  return '<span class="badge active">Active</span>';
}

export function viewLogin() {
  return `
    <div class="login-screen">
      <div class="login-box">
        <h2>IRON<span>LOG</span></h2>
        <div class="subtitle">Gym Management Portal</div>
        <form id="login-form">
          <div class="form-group">
            <label>Email Address</label>
            <input type="email" name="email" required placeholder="e.g. admin@ironlog.com" value="admin@ironlog.com">
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" required placeholder="••••••••" value="admin123">
          </div>
          <button type="submit" class="btn" style="margin-top:10px;justify-content:center;">Sign In</button>
        </form>
      </div>
    </div>
  `;
}

export function viewSidebar(user, currentView, navItems) {
  const email = user.email || 'user@ironlog.com';
  const roleMark = user.role === 'Admin' ? 'A' : (user.role === 'Trainer' ? 'T' : 'M');
  const roleLabel = user.role === 'Admin' ? 'Admin Staff' : (user.role === 'Trainer' ? 'Captain Trainer' : 'Gym Member');

  return `
    <aside class="sidebar">
      <div class="brand">
        <div class="mark">IRON<span>LOG</span></div>
        <div class="sub">SQL Gym Management</div>
      </div>
      <nav class="main-nav">
        ${navItems.map(([key, label]) => `
          <div class="navitem ${currentView === key ? 'active' : ''}" data-view="${key}">
            <span class="dot"></span>${label}
          </div>`).join('')}
      </nav>
      <div class="sidebar-foot" style="border-top:1px solid var(--line-strong);padding-top:16px;">
        <div class="userline" style="margin-bottom:12px;">
          <div class="avatar">${roleMark}</div>
          <div style="min-width:0;">
            <div style="font-weight:600;color:var(--chalk);text-overflow:ellipsis;overflow:hidden;white-space:nowrap;">${email}</div>
            <div style="font-size:10px;color:var(--chalk-faint);">${roleLabel}</div>
          </div>
        </div>
        <button id="logout-btn" class="btn small ghost" style="width:100%;justify-content:center;background:#2d1a19;color:var(--red);border-color:var(--red-dim);">Log Out</button>
      </div>
    </aside>
  `;
}

export function viewAdminDashboard(stats, liveOccupancy, peakHours, onCheckOut) {
  const currentStats = stats || { total_members: 0, active_members: 0, inside_gym: 0, today_check_ins: 0, total_trainers: 0, expiring_soon: 0, expired_members: 0 };
  return `
    <div class="pagehead">
      <div><div class="eyebrow">SQL Connected Overview</div><h1>Dashboard</h1></div>
      <div class="meta">${new Date().toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'})}</div>
    </div>
    
    <div class="statgrid">
      <div class="statcard"><div class="label">Total Members</div><div class="value">${currentStats.total_members}</div><div class="delta">${currentStats.active_members} active</div></div>
      <div class="statcard"><div class="label">Inside Gym Now</div><div class="value accent">${liveOccupancy.length}</div><div class="delta">vw_CurrentOccupancy</div></div>
      <div class="statcard"><div class="label">Today's Attendance</div><div class="value">${currentStats.today_check_ins}</div><div class="delta">check-in sessions</div></div>
      <div class="statcard"><div class="label">Total Trainers</div><div class="value">${currentStats.total_trainers}</div><div class="delta">active trainers</div></div>
      <div class="statcard"><div class="label">Expiring/Expired</div><div class="value ${currentStats.expiring_soon > 0 ? 'accent' : ''}">${(currentStats.expiring_soon || 0) + (currentStats.expired_members || 0)}</div><div class="delta warn">trg_SubscriptionExpiry</div></div>
    </div>

    ${viewLiveOccupancyPanel(liveOccupancy, onCheckOut)}

    <div class="panel">
      <div class="panel-head"><h3>Peak Hours Analysis (vw_PeakHours)</h3></div>
      <div class="panel-body">
        <table>
          <thead><tr><th>Time Slot</th><th>Total Check-Ins</th><th>Avg Duration (Mins)</th></tr></thead>
          <tbody>
            ${peakHours.map(p => `
              <tr>
                <td class="strong">${p.time_slot}</td>
                <td class="strong" style="color:var(--orange);">${p.total_check_ins} check-ins</td>
                <td>${p.avg_duration_minutes || 60} mins</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

export function viewLiveOccupancyPanel(liveOccupancy, onCheckOut) {
  const count = liveOccupancy.length;
  let level = 'empty', label = 'Quiet (0-15)';
  if (count >= 30) { level = 'full'; label = 'Crowded (30+)'; }
  else if (count >= 15) { level = 'normal'; label = 'Moderate (15-30)'; }

  return `
    <div class="gym-live-panel">
      <div class="gym-live-head">
        <div class="gym-live-title">
          <span class="live-dot"></span>
          <div>
            <div class="eyebrow">SQL Live Query</div>
            <h3>Who's In The Gym Right Now (vw_CurrentOccupancy)</h3>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          <div class="crowd-badge ${level}">${label}</div>
          <div class="mono" style="color:var(--chalk);font-size:15px;">${count} members inside</div>
          <button class="btn small ghost refresh-sql-btn">Refresh SQL</button>
        </div>
      </div>

      <div class="gym-live-body">
        <div class="table-container">
          <table>
            <thead><tr><th>Member</th><th>Phone</th><th>Plan</th><th>Check-In Time</th><th>Duration</th><th>Action</th></tr></thead>
            <tbody>
              ${liveOccupancy.length > 0 ? liveOccupancy.map(a => `
                <tr>
                  <td class="strong">${a.full_name}</td>
                  <td>${a.phone}</td>
                  <td><span class="badge active">${a.plan_name || 'Active Plan'}</span></td>
                  <td class="mono">${a.check_in_time}</td>
                  <td class="mono">${a.duration_minutes || 45} mins</td>
                  <td><button class="btn small check-out-direct-btn" data-att-id="${a.attendance_id}" data-mem-id="${a.member_id}" style="background:var(--red);color:#FFF;">Check-Out</button></td>
                </tr>
              `).join('') : `
                <tr><td colspan="6" class="empty">No members currently checked in to gym floor.</td></tr>
              `}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

export function viewAdminMembers(members, plans, trainers, searchVal, filterVal) {
  let list = members.filter(m => {
    const matchesSearch = (m.full_name + ' ' + (m.email || '') + ' ' + (m.phone || '')).toLowerCase().includes(searchVal.toLowerCase());
    const matchesStatus = filterVal === 'All' || m.membership_status === filterVal;
    return matchesSearch && matchesStatus;
  });

  return `
    <div class="pagehead">
      <div><div class="eyebrow">${members.length} Total Members</div><h1>Members Directory</h1></div>
      <button class="btn add-member-modal-btn">+ Register Member (sp_RegisterMember)</button>
    </div>

    <div class="panel">
      <div class="panel-body">
        <div class="searchbar">
          <input id="members-search" placeholder="Search by name, phone or email…" value="${searchVal}">
          <select id="members-filter">
            ${['All','Active','Expiring Soon','Expired','Inactive'].map(s => `<option ${filterVal === s ? 'selected' : ''}>${s}</option>`).join('')}
          </select>
        </div>

        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Contact</th><th>Plan</th><th>Expiry Date</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            ${list.map(m => `
              <tr>
                <td class="mono strong" style="color:var(--orange);">#${m.member_id}</td>
                <td class="strong">${m.full_name}</td>
                <td>📞 ${m.phone}<br><span style="font-size:11px;color:var(--chalk-faint);">${m.email || 'No email'}</span></td>
                <td><span class="badge active">${m.plan_name || 'Standard'}</span></td>
                <td class="mono">${m.end_date || 'N/A'}</td>
                <td>${subStatusBadge(m.membership_status)}</td>
                <td style="display:flex;gap:6px;">
                  <button class="btn small check-in-direct-btn" data-mem-id="${m.member_id}">Check-In</button>
                  <button class="btn small ghost renew-subscription-modal-btn" data-mem-id="${m.member_id}" data-plan-id="${m.plan_id || plans[0]?.plan_id}">Renew</button>
                </td>
              </tr>
            `).join('') || `<tr><td colspan="7" class="empty">No members found matching filters.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

export function viewAdminTrainers(trainers) {
  return `
    <div class="pagehead"><div><div class="eyebrow">${trainers.length} Total</div><h1>Trainers Directory</h1></div><button class="btn add-trainer-modal-btn">+ Add Trainer</button></div>
    <div class="panel"><div class="panel-body">
      <table>
        <thead><tr><th>ID</th><th>Name</th><th>Specialization</th><th>Assigned Members</th><th>Status</th></tr></thead>
        <tbody>
          ${trainers.map(t => `
            <tr>
              <td class="mono">#${t.trainer_id}</td>
              <td class="strong">${t.full_name}</td>
              <td style="color:var(--orange);">${t.specialization || 'General Fitness'}</td>
              <td class="strong">${t.assigned_member_count || 0} Members</td>
              <td><span class="badge active">${t.status}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div></div>
  `;
}

export function viewAdminPlans(plans) {
  return `
    <div class="pagehead"><div><div class="eyebrow">${plans.length} Available</div><h1>Subscription Plans</h1></div><button class="btn add-plan-modal-btn">+ Add Plan</button></div>
    <div class="grid-3">
      ${plans.map(p => `
        <div class="panel"><div class="panel-body">
          <div class="eyebrow" style="margin-bottom:8px;">${p.duration_months} Month(s)</div>
          <h2 style="font-size:24px;margin-bottom:6px;">${p.name}</h2>
          <div class="value mono" style="font-size:24px;color:var(--orange);margin-bottom:10px;">${p.price} EGP</div>
          <div style="font-size:13px;color:var(--chalk-dim);">${p.description || 'Full access to gym facilities.'}</div>
        </div></div>
      `).join('')}
    </div>
  `;
}

export function viewAdminAttendance(liveOccupancy, members, onCheckIn, onCheckOut) {
  return `
    <div class="pagehead"><div><div class="eyebrow">Live Log</div><h1>Attendance Station</h1></div></div>
    <div class="panel">
      <div class="panel-head"><h3>Record Quick Member Check-In</h3></div>
      <div class="panel-body" style="display:flex;gap:15px;align-items:center;">
        <select id="quick-checkin-select" style="flex:1;background:var(--iron);border:1px solid var(--line-strong);color:var(--chalk);padding:10px;">
          <option value="">-- Select Member to Check-In --</option>
          ${members.map(m => `<option value="${m.member_id}">${m.full_name} (${m.phone}) - ${m.membership_status}</option>`).join('')}
        </select>
        <button id="quick-checkin-btn" class="btn">Record Check-In</button>
      </div>
    </div>
    ${viewLiveOccupancyPanel(liveOccupancy, onCheckOut)}
  `;
}

export function viewAdminReports(daily, monthly) {
  return `
    <div class="pagehead">
      <div><div class="eyebrow">SQL Analytics</div><h1>Attendance Reports</h1></div>
      <button class="btn trigger-scheduler-run-btn" style="background:var(--olive);color:var(--iron);">Run Expiry Scheduler Audits</button>
    </div>
    <div class="grid-2">
      <div class="panel">
        <div class="panel-head"><h3>Daily Attendance Summary (vw_DailyAttendance)</h3></div>
        <div class="panel-body">
          <table>
            <thead><tr><th>Date</th><th>Total Visitors</th><th>Currently Inside</th></tr></thead>
            <tbody>
              ${daily.map(r => `
                <tr><td class="mono strong">${r.date}</td><td class="strong">${r.total_visitors} Visitors</td><td>${r.currently_inside} inside</td></tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Monthly Statistics (vw_MonthlyAttendance)</h3></div>
        <div class="panel-body">
          <table>
            <thead><tr><th>Month</th><th>Total Visits</th><th>Avg Daily</th></tr></thead>
            <tbody>
              ${monthly.map(m => `
                <tr><td class="mono strong">${m.month}</td><td class="strong">${m.total_visits} Visits</td><td>${m.avg_daily_attendance} / day</td></tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

export function viewNotificationsList(notifications) {
  return `
    <div class="pagehead"><div><div class="eyebrow">${notifications.length} Alerts</div><h1>Expiry Notifications Hub</h1></div></div>
    <div class="panel"><div class="panel-body">
      ${notifications.map(n => `
        <div class="notif-item">
          <div class="notif-dot ${n.alert_type === 'Expired' ? 'red' : 'orange'}"></div>
          <div class="notif-body">
            <div class="msg"><span class="strong">${n.member_name}</span> — ${n.message}</div>
            <div class="time">${n.alert_date || 'Today'} · Priority: ${n.alert_type || 'Warning'}</div>
          </div>
        </div>
      `).join('') || '<div class="empty">No active expiry notifications.</div>'}
    </div></div>
  `;
}

// Trainer Views
export function viewTrainerMembers(members, plans, trainers, searchVal, filterVal, trainerId) {
  const trainerMembers = members.filter(m => m.trainer_name && trainers.find(t => t.trainer_id === trainerId)?.full_name === m.trainer_name);
  return `
    <div class="pagehead">
      <div><div class="eyebrow">Your Assigned Clients</div><h1>My Members</h1></div>
    </div>
    <div class="panel">
      <div class="panel-body">
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Contact</th><th>Plan</th><th>Expiry Date</th><th>Status</th></tr></thead>
          <tbody>
            ${trainerMembers.map(m => `
              <tr>
                <td class="mono strong" style="color:var(--orange);">#${m.member_id}</td>
                <td class="strong">${m.full_name}</td>
                <td>📞 ${m.phone}<br><span style="font-size:11px;color:var(--chalk-faint);">${m.email || 'No email'}</span></td>
                <td><span class="badge active">${m.plan_name || 'Standard'}</span></td>
                <td class="mono">${m.end_date || 'N/A'}</td>
                <td>${subStatusBadge(m.membership_status)}</td>
              </tr>
            `).join('') || `<tr><td colspan="6" class="empty">You do not have any assigned members currently.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// Member Views
export function viewMemberDashboard(member, liveOccupancy, onCheckIn, onCheckOut) {
  const currentMember = member || { member_id: 1, full_name: 'Youssef Ahmed', membership_status: 'Active' };
  const checkedIn = liveOccupancy.some(o => o.member_id === currentMember.member_id);

  return `
    <div class="hero-card">
      <div>
        <div class="welcome-eyebrow">Welcome back</div>
        <h2>${currentMember.full_name}</h2>
        <div class="tag-row">
          <span class="tag gold">Membership: ${currentMember.membership_status || 'Active'}</span>
          <span class="tag">SQL Connected</span>
        </div>
      </div>
      <div class="checkin-block">
        <div class="checkin-status">
          <div>${checkedIn ? 'Currently inside gym' : 'Not checked in'}</div>
        </div>
        ${checkedIn 
          ? `<button class="btn check-out-self-btn" data-mem-id="${currentMember.member_id}" style="background:var(--red);color:#FFF;">Check Out</button>`
          : `<button class="btn check-in-self-btn" data-mem-id="${currentMember.member_id}">Check In</button>`
        }
      </div>
    </div>

    ${viewLiveOccupancyPanel(liveOccupancy, onCheckOut)}
  `;
}

export function viewMemberSubscription(member, plans, onRenew) {
  const currentMember = member || { member_id: 1, full_name: 'Youssef Ahmed', plan_name: 'Premium', plan_price: 2400.0, start_date: '2026-08-01', end_date: '2027-02-01', subscription_status: 'Active' };
  return `
    <div class="pagehead"><div><div class="eyebrow">Your Plan Details</div><h1>My Subscription</h1></div></div>
    <div class="grid-2">
      <div class="panel">
        <div class="panel-head"><h3>Active Subscription Info</h3></div>
        <div class="panel-body">
          <div class="plate-list">
            <div class="plate-row">
              <div class="plate-num">1</div>
              <div class="plate-info">
                <div class="name">Plan Type</div>
                <div class="sub">Assigned membership plan</div>
              </div>
              <div class="plate-metric"><div class="val">${currentMember.plan_name || 'None'}</div></div>
            </div>
            <div class="plate-row">
              <div class="plate-num">2</div>
              <div class="plate-info">
                <div class="name">Price</div>
                <div class="sub">Cost of the subscription</div>
              </div>
              <div class="plate-metric"><div class="val">${currentMember.plan_price || 0} EGP</div></div>
            </div>
            <div class="plate-row">
              <div class="plate-num">3</div>
              <div class="plate-info">
                <div class="name">Active Period</div>
                <div class="sub">Start date to end date</div>
              </div>
              <div class="plate-metric"><div class="val" style="font-size:12px;">${currentMember.start_date} to ${currentMember.end_date}</div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Available Plans for Upgrades/Renewals</h3></div>
        <div class="panel-body" style="display:flex;flex-direction:column;gap:12px;">
          ${plans.map(p => `
            <div style="border:1px solid var(--line-strong);padding:14px;display:flex;justify-content:space-between;align-items:center;">
              <div>
                <h4 style="color:var(--chalk);font-size:15px;">${p.name}</h4>
                <p style="font-size:11px;color:var(--chalk-faint);margin-top:2px;">${p.duration_months} Months · ${p.price} EGP</p>
              </div>
              <button class="btn small renew-self-plan-btn" data-plan-id="${p.plan_id}" data-mem-id="${currentMember.member_id}">Select</button>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `;
}
