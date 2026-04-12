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
        <p class="text-sm text-gray-500 mb-4">首次使用，请选择访问方式</p>
        <form id="init-form" class="space-y-3">
          <div class="space-y-2">
            <label class="flex items-center gap-3 p-3 rounded border dark:border-gray-600 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700">
              <input type="radio" name="auth-mode" value="no-password" checked class="shrink-0" />
              <div>
                <div class="font-medium">无需密码，直接访问</div>
                <div class="text-xs text-gray-500">适合个人本地使用</div>
              </div>
            </label>
            <label class="flex items-center gap-3 p-3 rounded border dark:border-gray-600 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700">
              <input type="radio" name="auth-mode" value="password" class="shrink-0" />
              <div>
                <div class="font-medium">启用密码保护</div>
                <div class="text-xs text-gray-500">每次进入需要输入密码</div>
              </div>
            </label>
          </div>
          <div id="password-fields" class="space-y-3 hidden">
            <div>
              <label for="init-password" class="block text-sm font-medium mb-1">密码</label>
              <input type="password" id="init-password" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2" minlength="8" />
            </div>
            <div>
              <label for="init-confirm" class="block text-sm font-medium mb-1">确认密码</label>
              <input type="password" id="init-confirm" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2" minlength="8" />
            </div>
          </div>
          <div id="init-error" class="text-red-600 text-sm hidden"></div>
          <button type="submit" class="w-full rounded bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 font-medium">完成初始化</button>
        </form>
      </div>
    </div>
  `;

  const authModeInputs = app.querySelectorAll('input[name="auth-mode"]');
  const passwordFields = app.querySelector('#password-fields');
  const passwordInput = app.querySelector('#init-password');
  const confirmInput = app.querySelector('#init-confirm');

  function updateFields() {
    const mode = app.querySelector('input[name="auth-mode"]:checked').value;
    if (mode === 'password') {
      passwordFields.classList.remove('hidden');
      passwordInput.required = true;
      confirmInput.required = true;
    } else {
      passwordFields.classList.add('hidden');
      passwordInput.required = false;
      confirmInput.required = false;
    }
  }

  authModeInputs.forEach(input => input.addEventListener('change', updateFields));
  updateFields();

  app.querySelector('#init-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const mode = app.querySelector('input[name="auth-mode"]:checked').value;
    const errEl = app.querySelector('#init-error');
    const payload = {
      password_enabled: mode === 'password',
    };

    if (mode === 'password') {
      const pwd = passwordInput.value;
      const confirm = confirmInput.value;
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
      payload.password = pwd;
    }

    const res = await apiPost('/system/init', payload);
    if (res.ok) {
      window.location.hash = '#/login';
    } else {
      errEl.textContent = res.error || '初始化失败';
      errEl.classList.remove('hidden');
    }
  });
}
