export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  const colors = {
    info: 'bg-blue-600',
    success: 'bg-green-600',
    warning: 'bg-yellow-500',
    error: 'bg-red-600'
  };
  el.className = `${colors[type] || colors.info} text-white px-4 py-2 rounded shadow transition-opacity duration-300`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

export function showModal({ title, body, actions = [] }) {
  const prevActive = document.activeElement;
  const backdrop = document.createElement('div');
  backdrop.setAttribute('role', 'dialog');
  backdrop.setAttribute('aria-modal', 'true');
  backdrop.setAttribute('aria-label', title || '对话框');
  backdrop.className = 'fixed inset-0 bg-black/50 z-40 flex items-center justify-center';
  backdrop.innerHTML = `
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden">
      <div class="px-4 py-3 border-b dark:border-gray-700 font-semibold">${escapeHtml(title)}</div>
      <div class="px-4 py-4">${typeof body === 'string' ? body : ''}</div>
      <div class="px-4 py-3 border-t dark:border-gray-700 flex justify-end gap-2" id="modal-actions"></div>
    </div>
  `;
  const actionsContainer = backdrop.querySelector('#modal-actions');
  const btns = [];
  actions.forEach(action => {
    const btn = document.createElement('button');
    btn.className = action.className || 'px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600';
    btn.textContent = action.label;
    btn.onclick = () => {
      if (typeof action.onClick === 'function') action.onClick();
      backdrop.remove();
      if (prevActive && prevActive.focus) prevActive.focus();
    };
    actionsContainer.appendChild(btn);
    btns.push(btn);
  });
  document.body.appendChild(backdrop);
  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) {
      backdrop.remove();
      if (prevActive && prevActive.focus) prevActive.focus();
    }
  });
  backdrop.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      backdrop.remove();
      if (prevActive && prevActive.focus) prevActive.focus();
    }
  });
  if (btns[0]) btns[0].focus();
  return backdrop;
}

export function renderSkeleton(container) {
  if (!container) return;
  container.innerHTML = `
    <div class="space-y-3 animate-pulse">
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
      <div class="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
    </div>
  `;
}

export function clearSkeleton(container) {
  if (container) container.innerHTML = '';
}

export function renderMarkdown(mdText) {
  if (typeof marked !== 'undefined' && marked.parse) {
    return marked.parse(mdText || '', { sanitize: true });
  }
  return escapeHtml(mdText || '').replace(/\n/g, '<br>');
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
