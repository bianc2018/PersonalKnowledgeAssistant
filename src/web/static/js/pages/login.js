import { apiPost } from '../api.js';
import { setToken } from '../store.js';

export function render() {
  const app = document.getElementById('app');
  const params = new URLSearchParams(window.location.hash.split('?')[1] || '');
  const redirect = params.get('redirect') || 'dashboard';

  app.innerHTML = `
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h1 class="text-xl font-bold mb-4">登录</h1>
        <form id="login-form" class="space-y-3">
          <div>
            <label for="login-password" class="block text-sm font-medium mb-1">密码</label>
            <input type="password" id="login-password" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2" required />
          </div>
          <div class="flex items-center gap-2">
            <input type="checkbox" id="login-remember" class="rounded" />
            <label for="login-remember" class="text-sm">记住我（7天）</label>
          </div>
          <div id="login-error" class="text-red-600 text-sm hidden"></div>
          <button type="submit" class="w-full rounded bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 font-medium">登录</button>
        </form>
      </div>
    </div>
  `;

  app.querySelector('#login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const pwd = app.querySelector('#login-password').value;
    const remember = app.querySelector('#login-remember').checked;
    const res = await apiPost('/auth/login', { password: pwd, remember_me: remember });
    if (res.ok && res.data && res.data.token) {
      setToken(res.data.token, remember);
      window.location.hash = `#/${redirect}`;
    } else {
      const errEl = app.querySelector('#login-error');
      errEl.textContent = res.error || '登录失败';
      errEl.classList.remove('hidden');
    }
  });
}
