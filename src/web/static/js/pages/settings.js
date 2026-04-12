import { apiGet, apiPut, apiExport, apiUpload, apiPost } from '../api.js';
import { renderSkeleton, clearSkeleton, showToast, showModal } from '../ui.js';
import { clearToken } from '../store.js';

function isMasked(val) {
  return typeof val === 'string' && val.endsWith('****');
}

export async function render() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
      <h1 class="text-2xl font-bold">系统设置</h1>
      <div id="settings-content"></div>
    </div>
  `;
  const container = app.querySelector('#settings-content');
  renderSkeleton(container);

  const res = await apiGet('/system/config');
  clearSkeleton(container);
  if (!res.ok) {
    container.innerHTML = `<div class="text-red-600">加载失败</div>`;
    return;
  }

  const cfg = res.data?.data || {};
  const llm = cfg.llm_config || {};
  const emb = cfg.embedding_config || {};
  const search = cfg.search_config || {};
  const privacy = cfg.privacy_settings || {};
  const retry = cfg.retry_settings || {};
  const storage = cfg.storage_settings || {};
  const log = cfg.log_settings || {};

  container.innerHTML = `
    <div class="bg-white dark:bg-gray-800 rounded shadow p-4 space-y-6">
      <!-- LLM -->
      <section>
        <h2 class="font-semibold mb-3">LLM 配置</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium mb-1">Base URL</label>
            <input type="text" id="llm-url" value="${llm.base_url || ''}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Model</label>
            <input type="text" id="llm-model" value="${llm.model || ''}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium mb-1">API Key</label>
            <input type="password" id="llm-key" value="${llm.api_key || ''}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
            <div class="text-xs text-gray-500 mt-1">若显示为 ****，留空表示不修改</div>
          </div>
        </div>
      </section>

      <!-- Embedding -->
      <section>
        <h2 class="font-semibold mb-3">Embedding 配置</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium mb-1">Base URL</label>
            <input type="text" id="emb-url" value="${emb.base_url || ''}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Model</label>
            <input type="text" id="emb-model" value="${emb.model || ''}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium mb-1">API Key</label>
            <input type="password" id="emb-key" value="${emb.api_key || ''}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
        </div>
      </section>

      <!-- Search -->
      <section>
        <h2 class="font-semibold mb-3">搜索 API</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium mb-1">Provider</label>
            <input type="text" id="search-provider" value="${search.provider || ''}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
        </div>
      </section>

      <!-- Privacy -->
      <section>
        <h2 class="font-semibold mb-3">隐私策略</h2>
        <div class="space-y-2">
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" id="privacy-full" ${privacy.allow_full_content ? 'checked' : ''} />
            <span>允许发送完整知识内容到 LLM</span>
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" id="privacy-web" ${privacy.allow_web_search !== false ? 'checked' : ''} />
            <span>允许使用外部网络搜索</span>
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" id="privacy-log" ${privacy.allow_log_upload ? 'checked' : ''} />
            <span>允许上传日志用于诊断</span>
          </label>
        </div>
      </section>

      <!-- Retry -->
      <section>
        <h2 class="font-semibold mb-3">重试设置</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium mb-1">重试次数</label>
            <input type="number" id="retry-times" value="${retry.retry_times ?? 3}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">超时（秒）</label>
            <input type="number" id="retry-timeout" value="${retry.timeout_seconds ?? 30}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
        </div>
      </section>

      <!-- Storage -->
      <section>
        <h2 class="font-semibold mb-3">存储与日志</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium mb-1">归档阈值（GB）</label>
            <input type="number" step="0.1" id="storage-archive" value="${storage.archive_threshold_gb ?? 10}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">日志保留（天）</label>
            <input type="number" id="log-retention" value="${log.retention_days ?? 30}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">日志级别</label>
            <select id="log-level" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm">
              <option value="DEBUG" ${(log.level || 'INFO') === 'DEBUG' ? 'selected' : ''}>DEBUG</option>
              <option value="INFO" ${(log.level || 'INFO') === 'INFO' ? 'selected' : ''}>INFO</option>
              <option value="WARNING" ${(log.level || 'INFO') === 'WARNING' ? 'selected' : ''}>WARNING</option>
              <option value="ERROR" ${(log.level || 'INFO') === 'ERROR' ? 'selected' : ''}>ERROR</option>
            </select>
          </div>
        </div>
      </section>

      <div class="flex gap-2 pt-2">
        <button id="btn-save-settings" class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">保存配置</button>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 rounded shadow p-4 space-y-4">
      <h2 class="font-semibold">数据操作</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div class="p-3 border dark:border-gray-700 rounded">
          <div class="font-medium text-sm mb-2">导出备份</div>
          <div class="flex gap-2">
            <input type="password" id="export-password" placeholder="当前密码" class="flex-1 rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
            <button id="btn-export" class="px-3 py-2 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">导出</button>
          </div>
        </div>
        <div class="p-3 border dark:border-gray-700 rounded">
          <div class="font-medium text-sm mb-2">导入备份</div>
          <div class="flex gap-2">
            <input type="file" id="import-file" accept=".zip,.enc" class="flex-1 text-sm" />
            <input type="password" id="import-password" placeholder="密码" class="flex-1 rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
            <button id="btn-import" class="px-3 py-2 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">导入</button>
          </div>
        </div>
        <div class="p-3 border dark:border-gray-700 rounded">
          <div class="font-medium text-sm mb-2">重置系统</div>
          <button id="btn-reset" class="w-full px-3 py-2 rounded bg-red-100 text-red-700 hover:bg-red-200 text-sm">重置所有数据</button>
        </div>
      </div>
    </div>
  `;

  container.querySelector('#btn-save-settings').addEventListener('click', async () => {
    const payload = {};
    const llmUrl = container.querySelector('#llm-url').value.trim();
    const llmModel = container.querySelector('#llm-model').value.trim();
    const llmKey = container.querySelector('#llm-key').value.trim();
    const llmUpdate = { base_url: llmUrl, model: llmModel };
    if (llmKey && !isMasked(llmKey)) llmUpdate.api_key = llmKey;
    payload.llm_config = llmUpdate;

    const embUrl = container.querySelector('#emb-url').value.trim();
    const embModel = container.querySelector('#emb-model').value.trim();
    const embKey = container.querySelector('#emb-key').value.trim();
    const embUpdate = { base_url: embUrl, model: embModel };
    if (embKey && !isMasked(embKey)) embUpdate.api_key = embKey;
    payload.embedding_config = embUpdate;

    payload.search_config = { provider: container.querySelector('#search-provider').value.trim() };

    payload.privacy_settings = {
      allow_full_content: container.querySelector('#privacy-full').checked,
      allow_web_search: container.querySelector('#privacy-web').checked,
      allow_log_upload: container.querySelector('#privacy-log').checked,
    };

    payload.retry_settings = {
      retry_times: parseInt(container.querySelector('#retry-times').value, 10) || 3,
      timeout_seconds: parseInt(container.querySelector('#retry-timeout').value, 10) || 30,
    };

    payload.storage_settings = {
      archive_threshold_gb: parseFloat(container.querySelector('#storage-archive').value) || 10,
    };

    payload.log_settings = {
      level: container.querySelector('#log-level').value,
      retention_days: parseInt(container.querySelector('#log-retention').value, 10) || 30,
    };

    const r = await apiPut('/system/config', payload);
    if (r.ok) showToast('配置已保存', 'success');
    else showToast(r.error || '保存失败', 'error');
  });

  container.querySelector('#btn-export').addEventListener('click', async () => {
    const pwd = container.querySelector('#export-password').value;
    if (!pwd) { showToast('请输入密码', 'warning'); return; }
    const r = await apiExport('/system/export', { password: pwd });
    if (r && r.ok && r.blob) {
      const url = URL.createObjectURL(r.blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'backup.zip.enc';
      a.click();
      URL.revokeObjectURL(url);
      showToast('导出成功', 'success');
    } else {
      showToast((r && r.error) || '导出失败', 'error');
    }
  });

  container.querySelector('#btn-import').addEventListener('click', async () => {
    const fileInput = container.querySelector('#import-file');
    const pwd = container.querySelector('#import-password').value;
    if (!fileInput.files || !fileInput.files[0]) { showToast('请选择文件', 'warning'); return; }
    if (!pwd) { showToast('请输入密码', 'warning'); return; }
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    fd.append('password', pwd);
    const r = await apiUpload('/system/import', fd);
    if (r.ok) {
      const data = r.data?.data || {};
      showToast(data.message || '导入成功', 'success');
      showModal({
        title: '导入结果',
        body: `<div class="text-sm space-y-1">
          <div>导入条目数：${data.imported_items || 0}</div>
          <div>跳过文件数：${(data.skipped_files || []).length}</div>
        </div>`,
        actions: [{ label: '确定', className: 'px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700' }]
      });
    } else {
      showToast(r.error || '导入失败', 'error');
    }
  });

  container.querySelector('#btn-reset').addEventListener('click', () => {
    showModal({
      title: '确认重置系统',
      body: `<div class="text-sm space-y-2">
        <div class="text-red-600 font-medium">警告：此操作将清除所有本地加密数据，不可恢复。</div>
        <div>
          <label class="block text-sm font-medium mb-1">请输入密码确认</label>
          <input type="password" id="reset-password" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div id="reset-error" class="text-red-600 text-sm hidden"></div>
      </div>`,
      actions: [
        { label: '取消', className: 'px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600' },
        { label: '确认重置', className: 'px-3 py-1.5 rounded bg-red-600 text-white hover:bg-red-700', onClick: async () => {
          const pwd = document.getElementById('reset-password').value;
          const errEl = document.getElementById('reset-error');
          if (!pwd) { if (errEl) { errEl.textContent = '请输入密码'; errEl.classList.remove('hidden'); } return; }
          const r = await apiPost('/system/reset', { password: pwd });
          if (r.ok) {
            clearToken();
            showToast('系统已重置', 'success');
            window.location.hash = '#/init';
          } else {
            if (errEl) { errEl.textContent = r.error || '重置失败'; errEl.classList.remove('hidden'); }
          }
        }}
      ]
    });
  });
}
