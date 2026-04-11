import { apiPost } from '../api.js';
import { apiGet } from '../api.js';

export async function render() {
  const statusRes = await apiGet('/system/status');
  const alreadyInit = statusRes.ok && statusRes.data && statusRes.data.initialized;
  if (alreadyInit) {
    window.location.hash = '#/login';
    return;
  }
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h1 class="text-xl font-bold mb-2">系统初始化</h1>
        <p class="text-sm text-gray-500 mb-4">首次使用，请设置管理密码（≥8位，包含字母和数字）</p>
        <form id="init-form" class="space-y-3">
          <div>
            <label for="init-password" class="block text-sm font-medium mb-1">密码</label>
            <input type="password" id="init-password" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2" required minlength="8" />
          </div>
          <div>
            <label for="init-confirm" class="block text-sm font-medium mb-1">确认密码</label>
            <input type="password" id="init-confirm" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2" required minlength="8" />
          </div>
          <div id="init-error" class="text-red-600 text-sm hidden"></div>
          <button type="submit" class="w-full rounded bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 font-medium">完成初始化</button>
        </form>
      </div>
    </div>
  `;

  app.querySelector('#init-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const pwd = app.querySelector('#init-password').value;
    const confirm = app.querySelector('#init-confirm').value;
    const errEl = app.querySelector('#init-error');
    if (pwd !== confirm) {
      errEl.textContent = '两次输入的密码不一致';
      errEl.classList.remove('hidden');
      return;
    }
    if (!/[a-zA-Z]/.test(pwd) || !/\d/.test(pwd)) {
      errEl.textContent = '密码必须同时包含字母和数字';
      errEl.classList.remove('hidden');
      return;
    }
    const res = await apiPost('/system/init', { password: pwd });
    if (res.ok) {
      window.location.hash = '#/login';
    } else {
      errEl.textContent = res.error || '初始化失败';
      errEl.classList.remove('hidden');
    }
  });
}
