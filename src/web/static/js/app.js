import { initRouter } from './router.js';
import { getToken } from './store.js';

import * as initPage from './pages/init.js';
import * as loginPage from './pages/login.js';
import * as dashboardPage from './pages/dashboard.js';
import * as knowledgePage from './pages/knowledge.js';
import * as chatPage from './pages/chat.js';
import * as researchPage from './pages/research.js';
import * as settingsPage from './pages/settings.js';

window.pages = {
  init: initPage,
  login: loginPage,
  dashboard: dashboardPage,
  knowledge: knowledgePage,
  chat: chatPage,
  research: researchPage,
  settings: settingsPage,
};

const navItems = [
  { label: 'Dashboard', hash: '#/dashboard', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>' },
  { label: 'Knowledge', hash: '#/knowledge', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>' },
  { label: 'Chat', hash: '#/chat', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>' },
  { label: 'Research', hash: '#/research', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>' },
  { label: 'Settings', hash: '#/settings', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>' },
];

function renderNav() {
  const container = document.getElementById('nav-links');
  if (!container) return;
  const raw = window.location.hash.replace(/^#\/?/, '') || '';
  const currentBase = raw.split('/')[0] || 'dashboard';
  container.innerHTML = navItems.map(item => {
    const active = currentBase === item.hash.replace('#/', '').split('/')[0]
      ? 'bg-gray-100 dark:bg-gray-700 font-medium'
      : 'hover:bg-gray-100 dark:hover:bg-gray-700';
    return `<a href="${item.hash}" class="flex items-center gap-3 px-3 py-2 rounded ${active} text-sm">
      ${item.icon}
      <span>${item.label}</span>
    </a>`;
  }).join('');

  const footer = document.getElementById('nav-footer');
  if (footer) {
    const token = getToken();
    footer.innerHTML = token ? '<span class="text-green-600">●</span> 已登录' : '<span class="text-gray-400">●</span> 未登录';
  }
}

window.addEventListener('hashchange', renderNav);

document.addEventListener('DOMContentLoaded', () => {
  renderNav();
  initRouter();
});
