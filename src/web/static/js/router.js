import { getToken } from './store.js';

const routes = [
  { pattern: /^$/, redirect: 'dashboard' },
  { pattern: /^login$/, page: 'login', public: true },
  { pattern: /^init$/, page: 'init', public: true },
  { pattern: /^dashboard$/, page: 'dashboard' },
  { pattern: /^knowledge$/, page: 'knowledge', action: 'renderList' },
  { pattern: /^knowledge\/(.+)$/, page: 'knowledge', action: 'renderDetail', argIndex: 1 },
  { pattern: /^chat$/, page: 'chat', action: 'render' },
  { pattern: /^chat\/(.+)$/, page: 'chat', action: 'render', argIndex: 1 },
  { pattern: /^research$/, page: 'research', action: 'renderList' },
  { pattern: /^research\/(.+)$/, page: 'research', action: 'renderDetail', argIndex: 1 },
  { pattern: /^settings$/, page: 'settings' }
];

function matchRoute(hashPath) {
  for (const r of routes) {
    const m = hashPath.match(r.pattern);
    if (m) return { route: r, match: m };
  }
  return null;
}

export async function resolve() {
  const raw = window.location.hash.replace(/^#\/?/, '');
  const matched = matchRoute(raw);

  if (!matched) {
    window.location.hash = '#/dashboard';
    return;
  }

  const { route, match } = matched;

  if (route.redirect) {
    window.location.hash = `#/${route.redirect}`;
    return;
  }

  if (!route.public && !getToken()) {
    const redirect = raw ? `?redirect=${encodeURIComponent(raw)}` : '';
    window.location.hash = `#/login${redirect}`;
    return;
  }

  const pageModule = window.pages?.[route.page];
  if (!pageModule) {
    console.error(`Page module not found: ${route.page}`);
    return;
  }

  const action = route.action || 'render';
  const args = route.argIndex !== undefined ? [match[route.argIndex]] : [];
  try {
    if (typeof pageModule[action] === 'function') {
      await pageModule[action](...args);
    } else if (typeof pageModule.render === 'function') {
      await pageModule.render(...args);
    } else {
      console.error(`No render function on page module: ${route.page}`);
    }
  } catch (err) {
    console.error('Route render error:', err);
  }
}

export function initRouter() {
  window.addEventListener('hashchange', () => resolve());
  resolve();
}
