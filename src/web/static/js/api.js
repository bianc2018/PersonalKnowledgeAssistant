import { getToken, clearToken, addToast } from './store.js';

const BASE = '/api';

function getHeaders(isJson = true) {
  const h = {};
  if (isJson) h['Content-Type'] = 'application/json';
  const t = getToken();
  if (t) h['Authorization'] = `Bearer ${t}`;
  return h;
}

async function handleResponse(res) {
  if (res.status === 401) {
    clearToken();
    addToast('登录已过期，请重新登录', 'error');
    const current = window.location.hash.slice(1) || '';
    const redirect = current && current !== 'login' ? `?redirect=${encodeURIComponent(current)}` : '';
    window.location.hash = `#/login${redirect}`;
    return { ok: false, status: 401, error: 'Unauthorized' };
  }
  if (!res.ok) {
    let error = res.statusText;
    try {
      const body = await res.json();
      error = body.detail || body.error || JSON.stringify(body);
    } catch {
      try {
        error = await res.text();
      } catch {}
    }
    return { ok: false, status: res.status, error };
  }
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return { ok: true, data: await res.json() };
  }
  return { ok: true, data: await res.text() };
}

export async function apiGet(path, query = {}) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null) q.set(k, String(v));
  }
  const qs = q.toString();
  const url = `${BASE}${path}${qs ? '?' + qs : ''}`;
  const res = await fetch(url, { headers: getHeaders(false) });
  return handleResponse(res);
}

export async function apiPost(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: getHeaders(true),
    body: JSON.stringify(body)
  });
  return handleResponse(res);
}

export async function apiPatch(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: getHeaders(true),
    body: JSON.stringify(body)
  });
  return handleResponse(res);
}

export async function apiDelete(path) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'DELETE',
    headers: getHeaders(false)
  });
  return handleResponse(res);
}

export async function apiUpload(path, formData) {
  const h = getHeaders(false);
  delete h['Content-Type'];
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: h,
    body: formData
  });
  return handleResponse(res);
}

export async function apiExport(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: getHeaders(true),
    body: JSON.stringify(body)
  });
  if (res.status === 401) {
    clearToken();
    addToast('登录已过期，请重新登录', 'error');
    const current = window.location.hash.slice(1) || '';
    const redirect = current && current !== 'login' ? `?redirect=${encodeURIComponent(current)}` : '';
    window.location.hash = `#/login${redirect}`;
    return null;
  }
  if (!res.ok) {
    let error = res.statusText;
    try {
      const body = await res.json();
      error = body.detail || body.error || JSON.stringify(body);
    } catch {
      try { error = await res.text(); } catch {}
    }
    return { ok: false, status: res.status, error };
  }
  const blob = await res.blob();
  return { ok: true, blob };
}
