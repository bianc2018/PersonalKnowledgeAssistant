export const store = {
  token: null,
  user: null,
  currentPage: '',
  toasts: []
};

export function getToken() {
  if (store.token) return store.token;
  const ls = localStorage.getItem('pka_token');
  if (ls) {
    store.token = ls;
    return ls;
  }
  const ss = sessionStorage.getItem('pka_token');
  if (ss) {
    store.token = ss;
    return ss;
  }
  return null;
}

export function setToken(t, remember) {
  store.token = t;
  if (remember) {
    localStorage.setItem('pka_token', t);
    sessionStorage.removeItem('pka_token');
  } else {
    sessionStorage.setItem('pka_token', t);
    localStorage.removeItem('pka_token');
  }
}

export function clearToken() {
  store.token = null;
  localStorage.removeItem('pka_token');
  sessionStorage.removeItem('pka_token');
}

let _toastId = 0;

export function addToast(msg, type = 'info') {
  const id = ++_toastId;
  const toast = { id, msg, type };
  store.toasts.push(toast);
  setTimeout(() => removeToast(id), 3000);
  return toast;
}

export function removeToast(id) {
  const idx = store.toasts.findIndex(t => t.id === id);
  if (idx !== -1) store.toasts.splice(idx, 1);
}
