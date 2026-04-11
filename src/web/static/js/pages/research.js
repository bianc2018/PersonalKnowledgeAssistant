import { apiGet, apiPost } from '../api.js';
import { createSSEStream } from '../sse.js';
import { renderSkeleton, clearSkeleton, renderMarkdown, showToast, showModal, escapeHtml } from '../ui.js';
import { getToken } from '../store.js';

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return isNaN(d) ? iso : `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

function statusBadge(status) {
  const map = {
    queued: { cls: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200', label: '排队中' },
    running: { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200', label: '运行中' },
    awaiting_input: { cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-200', label: '等待输入' },
    completed: { cls: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200', label: '已完成' },
    error: { cls: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200', label: '错误' },
    degraded: { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-200', label: '降级' },
    pending_recheck: { cls: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200', label: '待复核' },
  };
  const m = map[status] || { cls: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200', label: status || '-' };
  return `<span class="inline-block px-2 py-0.5 rounded text-xs ${m.cls}">${m.label}</span>`;
}

let listState = { offset: 0, limit: 20, total: 0 };

export async function renderList() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="p-4 md:p-6 max-w-5xl mx-auto space-y-4">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-bold">调研任务</h1>
        <button id="btn-new-research" class="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">+ 新建调研</button>
      </div>
      <div id="list-content"></div>
    </div>
  `;
  const container = app.querySelector('#list-content');
  renderSkeleton(container);
  await loadList();

  app.querySelector('#btn-new-research').addEventListener('click', () => openNewResearchModal());
}

async function loadList() {
  const container = document.getElementById('list-content');
  const res = await apiGet('/research', { offset: listState.offset, limit: listState.limit });
  clearSkeleton(container);
  if (!res.ok) {
    container.innerHTML = `<div class="text-red-600">加载失败</div>`;
    return;
  }
  const items = res.data?.data || [];
  const pagination = res.data?.pagination || { total: 0, offset: 0, limit: 20 };
  listState.total = pagination.total;

  const hasPrev = listState.offset > 0;
  const hasNext = listState.offset + listState.limit < listState.total;

  container.innerHTML = `
    <div class="space-y-3">
      ${items.length ? items.map(t => `
        <div class="bg-white dark:bg-gray-800 rounded shadow p-4 flex flex-col gap-2">
          <div class="flex items-start justify-between gap-2">
            <a href="#/research/${t.id}" class="font-semibold text-blue-600 hover:underline">${escapeHtml(t.topic || '无主题')}</a>
            <div class="shrink-0">${statusBadge(t.status)}</div>
          </div>
          <div class="text-sm text-gray-500">进度: ${t.progress_percent ?? 0}% · ${fmtDate(t.created_at)}</div>
          ${t.scope_description ? `<div class="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">${escapeHtml(t.scope_description)}</div>` : ''}
        </div>
      `).join('') : '<div class="text-gray-500">暂无调研任务</div>'}
    </div>
    <div class="flex items-center justify-between pt-4">
      <button id="page-prev" class="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm ${hasPrev ? '' : 'opacity-50 cursor-not-allowed'}" ${hasPrev ? '' : 'disabled'}>上一页</button>
      <span class="text-sm text-gray-500">${listState.offset + 1} - ${Math.min(listState.offset + listState.limit, listState.total)} / ${listState.total}</span>
      <button id="page-next" class="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm ${hasNext ? '' : 'opacity-50 cursor-not-allowed'}" ${hasNext ? '' : 'disabled'}>下一页</button>
    </div>
  `;

  const prevBtn = container.querySelector('#page-prev');
  const nextBtn = container.querySelector('#page-next');
  if (prevBtn && hasPrev) prevBtn.addEventListener('click', async () => { listState.offset -= listState.limit; renderSkeleton(container); await loadList(); });
  if (nextBtn && hasNext) nextBtn.addEventListener('click', async () => { listState.offset += listState.limit; renderSkeleton(container); await loadList(); });
}

function openNewResearchModal() {
  const backdrop = document.createElement('div');
  backdrop.className = 'fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4';
  backdrop.innerHTML = `
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh]">
      <div class="px-4 py-3 border-b dark:border-gray-700 font-semibold">新建调研</div>
      <div class="p-4 overflow-auto space-y-3">
        <div>
          <label class="block text-sm font-medium mb-1">主题 <span class="text-red-500">*</span></label>
          <input type="text" id="nr-topic" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">范围描述</label>
          <textarea id="nr-scope" rows="4" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" placeholder="可选：补充调研范围、侧重点等"></textarea>
        </div>
        <div id="nr-error" class="text-red-600 text-sm hidden"></div>
      </div>
      <div class="px-4 py-3 border-t dark:border-gray-700 flex justify-end gap-2">
        <button id="nr-cancel" class="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">取消</button>
        <button id="nr-submit" class="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">提交</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
  backdrop.querySelector('#nr-cancel').addEventListener('click', close);
  backdrop.querySelector('#nr-submit').addEventListener('click', async () => {
    const topic = backdrop.querySelector('#nr-topic').value.trim();
    const scope = backdrop.querySelector('#nr-scope').value.trim();
    const err = backdrop.querySelector('#nr-error');
    if (!topic) { err.textContent = '请输入主题'; err.classList.remove('hidden'); return; }
    const res = await apiPost('/research', { topic, scope_description: scope });
    if (res.ok && res.data && res.data.id) {
      showToast('调研任务已创建', 'success');
      close();
      window.location.hash = `#/research/${res.data.id}`;
    } else {
      err.textContent = res.error || '创建失败';
      err.classList.remove('hidden');
    }
  });
}

export async function renderDetail(taskId) {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
      <div class="flex items-center gap-2 text-sm">
        <a href="#/research" class="text-blue-600 hover:underline">← 返回列表</a>
      </div>
      <div id="detail-content"></div>
    </div>
  `;
  const container = app.querySelector('#detail-content');
  renderSkeleton(container);

  const res = await apiGet(`/research/${taskId}`);
  clearSkeleton(container);
  if (!res.ok) {
    container.innerHTML = `<div class="text-red-600">加载失败：${escapeHtml(res.error || '')}</div>`;
    return;
  }
  const task = res.data?.data;
  if (!task) {
    container.innerHTML = `<div class="text-red-600">任务不存在</div>`;
    return;
  }

  let reportHtml = '';
  let questionHtml = '';
  let chunksHtml = '';
  let progress = task.progress_percent || 0;
  let status = task.status || 'queued';

  container.innerHTML = `
    <div class="bg-white dark:bg-gray-800 rounded shadow p-4 space-y-4">
      <div class="flex items-start justify-between gap-2">
        <div>
          <h1 class="text-xl font-bold">${escapeHtml(task.topic || '无主题')}</h1>
          <div class="text-xs text-gray-500 mt-1">创建于 ${fmtDate(task.created_at)}</div>
        </div>
        <div id="detail-status">${statusBadge(status)}</div>
      </div>

      <div>
        <div class="flex items-center justify-between text-sm mb-1">
          <span>进度</span>
          <span id="progress-text">${progress}%</span>
        </div>
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded h-2">
          <div id="progress-bar" class="bg-blue-600 h-2 rounded transition-all" style="width: ${progress}%"></div>
        </div>
      </div>

      <div id="question-area" class="${questionHtml ? '' : 'hidden'}"></div>

      <div id="chunks-area" class="space-y-2 ${chunksHtml ? '' : 'hidden'}">
        <h3 class="font-semibold text-sm">过程摘要</h3>
        <div id="chunks-content" class="text-sm text-gray-700 dark:text-gray-300 space-y-1"></div>
      </div>

      <div id="report-area" class="${reportHtml ? '' : 'hidden'}">
        <h3 class="font-semibold text-sm mb-2">调研报告</h3>
        <div id="report-content" class="prose dark:prose-invert max-w-none text-sm bg-gray-50 dark:bg-gray-700 rounded p-3"></div>
        <div class="mt-3">
          <button id="btn-save-report" class="px-3 py-2 rounded bg-green-600 text-white hover:bg-green-700 text-sm">保存到知识库</button>
        </div>
      </div>

      ${task.error_message ? `<div class="text-red-600 text-sm">错误：${escapeHtml(task.error_message || '')}</div>` : ''}
    </div>
  `;

  function updateStatus(s) {
    status = s;
    const el = container.querySelector('#detail-status');
    if (el) el.innerHTML = statusBadge(s);
  }

  function updateProgress(pct, msg) {
    progress = pct;
    const bar = container.querySelector('#progress-bar');
    const text = container.querySelector('#progress-text');
    if (bar) bar.style.width = `${pct}%`;
    if (text) text.textContent = `${pct}%${msg ? ' · ' + msg : ''}`;
  }

  function appendChunk(text) {
    const area = container.querySelector('#chunks-area');
    const content = container.querySelector('#chunks-content');
    area.classList.remove('hidden');
    const line = document.createElement('div');
    line.textContent = text;
    content.appendChild(line);
  }

  function showQuestion(q) {
    const area = container.querySelector('#question-area');
    area.classList.remove('hidden');
    area.innerHTML = `
      <div class="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded p-3">
        <div class="font-medium text-sm mb-2">${escapeHtml(q.question)}</div>
        <form id="question-form" class="space-y-2">
          ${(q.options || []).map((opt, idx) => `
            <label class="flex items-center gap-2 text-sm">
              <input type="radio" name="answer" value="${escapeHtml(opt)}" ${idx === 0 ? 'checked' : ''} />
              <span>${escapeHtml(opt)}</span>
            </label>
          `).join('')}
          <div>
            <label class="block text-sm font-medium mt-2">补充说明（可选）</label>
            <input type="text" id="question-custom" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" placeholder="自定义输入" />
          </div>
          <div class="flex gap-2 pt-1">
            <button type="submit" class="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">提交</button>
          </div>
        </form>
        <div id="question-error" class="text-red-600 text-sm hidden mt-2"></div>
      </div>
    `;
    area.querySelector('#question-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const answer = form.answer.value;
      const custom = area.querySelector('#question-custom').value.trim();
      const err = area.querySelector('#question-error');
      const r = await apiPost(`/research/${taskId}/respond`, { answer, custom_input: custom || undefined });
      if (r.ok) {
        area.classList.add('hidden');
        area.innerHTML = '';
        showToast('决策已提交', 'success');
        updateStatus('running');
      } else {
        err.textContent = r.error || '提交失败';
        err.classList.remove('hidden');
      }
    });
  }

  function showReport(content) {
    const area = container.querySelector('#report-area');
    const rc = container.querySelector('#report-content');
    area.classList.remove('hidden');
    rc.innerHTML = renderMarkdown(content);
  }

  const saveBtn = container.querySelector('#btn-save-report');
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const r = await apiPost(`/research/${taskId}/save`);
      if (r.ok && r.data && r.data.item_id) {
        showToast('报告已保存到知识库', 'success');
      } else {
        showToast(r.error || '保存失败', 'error');
      }
    });
  }

  // Open SSE stream
  const token = getToken();
  const sse = createSSEStream(`/api/research/${taskId}/events`, {
    onEvent: (type, data) => {
      if (data.status) updateStatus(data.status);
      if (type === 'status' && data.status) updateStatus(data.status);
      if (type === 'progress') updateProgress(data.percent ?? data.progress_percent ?? progress, data.message);
      if (type === 'chunk') appendChunk(data.content || data.raw || '');
      if (type === 'question') showQuestion(data);
      if (type === 'report') {
        updateStatus('completed');
        updateProgress(100, '');
        showReport(data.content || data.report || '');
      }
      if (type === 'error') {
        showToast(data.message || '调研出错', 'error');
        updateStatus('error');
      }
    },
    onError: (data) => {
      showToast(data.message || '连接中断', 'error');
    }
  }, token);
}
