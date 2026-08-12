/**
 * Central API fetch client and authentication utility.
 */

const API_BASE = window.location.origin + '/api';

export function getToken() {
  return 'mock_token';
}

export function setSession(token, role, referenceId, email) {
  localStorage.setItem('ironlog_token', token);
  localStorage.setItem('ironlog_role', role);
  localStorage.setItem('ironlog_ref_id', referenceId !== null && referenceId !== undefined ? referenceId : '');
  localStorage.setItem('ironlog_email', email);
}

export function clearSession() {
  localStorage.removeItem('ironlog_token');
  localStorage.removeItem('ironlog_role');
  localStorage.removeItem('ironlog_ref_id');
  localStorage.removeItem('ironlog_email');
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
  try {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}${endpoint}`, opts);
    
    if (res.status === 401) {
      // Token expired or invalid: force logout
      clearSession();
      window.dispatchEvent(new Event('auth_changed'));
      return null;
    }
    
    const json = await res.json();
    return json;
  } catch (err) {
    console.warn(`API fetch error on ${endpoint}:`, err);
    return null;
  }
}
