import { apiGet, apiPost, apiPatch, apiDelete, apiUpload } from '../api.js';
import { renderSkeleton, clearSkeleton, renderMarkdown, showToast, showModal } from '../ui.js';

// helpers
function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return isNaN(d) ? iso : `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

function confidenceBadge(level) {
  const map = {
    high: { cls: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200', label: '高' },
    medium: { cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-200', label: '中' },
    low: { cls: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200', label: '低' },
  };
  const m = map[level] || { cls: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200', label: level || '-' };
  return `<span class="inline-block px-2 py-0.5 rounded text-xs ${m.cls}">${m.label}</span>`;
}

let listState = { q: '', tags: '', offset: 0, limit: 20, total: 0 };

export async function renderList() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="p-4 md:p-6 max-w-5xl mx-auto space-y-4">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <h1 class="text-xl font-bold">知识库</h1>
        <div class="flex gap-2">
          <button id="btn-add-text" class="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">+ 文本</button>
          <button id="btn-add-file" class="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">+ 文件</button>
          <button id="btn-add-url" class="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">+ URL</button>
        </div>
      </div>
      <div class="flex flex-col md:flex-row gap-2">
        <input type="text" id="search-q" value="${listState.q}" placeholder="搜索知识..." aria-label="搜索知识" class="flex-1 rounded border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm" />
        <input type="text" id="search-tags" value="${listState.tags}" placeholder="标签过滤（逗号分隔）" aria-label="标签过滤" class="md:w-64 rounded border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm" />
        <button id="btn-search" class="px-4 py-2 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">搜索</button>
      </div>
      <div id="list-content"></div>
    </div>
  `;

  const container = app.querySelector('#list-content');
  renderSkeleton(container);

  await loadList();

  const doSearch = async () => {
    listState.q = app.querySelector('#search-q').value.trim();
    listState.tags = app.querySelector('#search-tags').value.trim();
    listState.offset = 0;
    renderSkeleton(container);
    await loadList();
  };

  let searchDebounce;
  app.querySelector('#search-q').addEventListener('input', () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(doSearch, 350);
  });
  app.querySelector('#search-q').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { clearTimeout(searchDebounce); doSearch(); }
  });
  app.querySelector('#search-tags').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { clearTimeout(searchDebounce); doSearch(); }
  });
  app.querySelector('#btn-search').addEventListener('click', doSearch);

  app.querySelector('#btn-add-text').addEventListener('click', () => openCreateTextModal());
  app.querySelector('#btn-add-file').addEventListener('click', () => openCreateFileModal());
  app.querySelector('#btn-add-url').addEventListener('click', () => openCreateUrlModal());
}

async function loadList() {
  const container = document.getElementById('list-content');
  const res = await apiGet('/knowledge', { q: listState.q, tags: listState.tags, offset: listState.offset, limit: listState.limit });
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
      ${items.length ? items.map(k => `
        <div class="bg-white dark:bg-gray-800 rounded shadow p-4 flex flex-col gap-2">
          <div class="flex items-start justify-between gap-2">
            <a href="#/knowledge/${k.id}" class="font-semibold text-blue-600 hover:underline">${k.title || '无标题'}</a>
            <div class="flex items-center gap-2 shrink-0">
              ${k.confidence ? confidenceBadge(k.confidence.score_level) : ''}
              ${k.is_deleted ? '<span class="text-xs text-gray-500">已删除</span>' : ''}
            </div>
          </div>
          <div class="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
            ${k.source_type ? `[${k.source_type}]` : ''} ${(k.tags || []).map(t => `<span class="inline-block mr-1 px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-xs">${t.name}</span>`).join('')}
          </div>
          <div class="text-xs text-gray-500">创建于 ${fmtDate(k.created_at)} · ${k.version_count || 1} 个版本</div>
        </div>
      `).join('') : '<div class="text-gray-500">暂无知识</div>'}
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

function openCreateTextModal() {
  const backdrop = document.createElement('div');
  backdrop.className = 'fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4';
  backdrop.innerHTML = `
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh]">
      <div class="px-4 py-3 border-b dark:border-gray-700 font-semibold">新建文本知识</div>
      <div class="p-4 overflow-auto space-y-3">
        <div>
          <label class="block text-sm font-medium mb-1">标题</label>
          <input type="text" id="ct-title" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">内容 <span class="text-red-500">*</span></label>
          <textarea id="ct-content" rows="6" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" placeholder="至少输入5个字符"></textarea>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">标签（逗号分隔）</label>
          <input type="text" id="ct-tags" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div id="ct-error" class="text-red-600 text-sm hidden"></div>
      </div>
      <div class="px-4 py-3 border-t dark:border-gray-700 flex justify-end gap-2">
        <button id="ct-cancel" class="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">取消</button>
        <button id="ct-submit" class="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">保存</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
  backdrop.querySelector('#ct-cancel').addEventListener('click', close);
  backdrop.querySelector('#ct-submit').addEventListener('click', async () => {
    const title = backdrop.querySelector('#ct-title').value.trim();
    const content = backdrop.querySelector('#ct-content').value.trim();
    const tags = backdrop.querySelector('#ct-tags').value.split(',').map(s => s.trim()).filter(Boolean);
    const err = backdrop.querySelector('#ct-error');
    if (content.length < 5) { err.textContent = '内容长度必须 ≥5'; err.classList.remove('hidden'); return; }
    const res = await apiPost('/knowledge', { title, content, tags, source_type: 'text' });
    if (res.ok) { showToast('创建成功', 'success'); close(); window.location.hash = `#/knowledge/${res.data.data.id}`; }
    else { err.textContent = res.error || '创建失败'; err.classList.remove('hidden'); }
  });
}

function openCreateFileModal() {
  const backdrop = document.createElement('div');
  backdrop.className = 'fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4';
  backdrop.innerHTML = `
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh]">
      <div class="px-4 py-3 border-b dark:border-gray-700 font-semibold">上传文件</div>
      <div class="p-4 overflow-auto space-y-3">
        <div>
          <label class="block text-sm font-medium mb-1">文件 <span class="text-red-500">*</span></label>
          <input type="file" id="cf-file" class="w-full text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">标题</label>
          <input type="text" id="cf-title" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">标签（逗号分隔）</label>
          <input type="text" id="cf-tags" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div id="cf-error" class="text-red-600 text-sm hidden"></div>
      </div>
      <div class="px-4 py-3 border-t dark:border-gray-700 flex justify-end gap-2">
        <button id="cf-cancel" class="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">取消</button>
        <button id="cf-submit" class="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">上传</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
  backdrop.querySelector('#cf-cancel').addEventListener('click', close);
  backdrop.querySelector('#cf-submit').addEventListener('click', async () => {
    const fileInput = backdrop.querySelector('#cf-file');
    const title = backdrop.querySelector('#cf-title').value.trim();
    const tags = backdrop.querySelector('#cf-tags').value.split(',').map(s => s.trim()).filter(Boolean).join(',');
    const err = backdrop.querySelector('#cf-error');
    if (!fileInput.files || !fileInput.files[0]) { err.textContent = '请选择文件'; err.classList.remove('hidden'); return; }
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    if (title) fd.append('title', title);
    if (tags) fd.append('tags', tags);
    const res = await apiUpload('/knowledge/upload', fd);
    if (res.ok) { showToast('上传成功', 'success'); close(); window.location.hash = `#/knowledge/${res.data.data.id}`; }
    else { err.textContent = res.error || '上传失败'; err.classList.remove('hidden'); }
  });
}

function openCreateUrlModal() {
  const backdrop = document.createElement('div');
  backdrop.className = 'fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4';
  backdrop.innerHTML = `
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh]">
      <div class="px-4 py-3 border-b dark:border-gray-700 font-semibold">添加 URL</div>
      <div class="p-4 overflow-auto space-y-3">
        <div>
          <label class="block text-sm font-medium mb-1">URL <span class="text-red-500">*</span></label>
          <input type="url" id="cu-url" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" placeholder="https://..." />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">标题</label>
          <input type="text" id="cu-title" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">标签（逗号分隔）</label>
          <input type="text" id="cu-tags" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div id="cu-error" class="text-red-600 text-sm hidden"></div>
      </div>
      <div class="px-4 py-3 border-t dark:border-gray-700 flex justify-end gap-2">
        <button id="cu-cancel" class="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">取消</button>
        <button id="cu-submit" class="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">保存</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
  backdrop.querySelector('#cu-cancel').addEventListener('click', close);
  backdrop.querySelector('#cu-submit').addEventListener('click', async () => {
    const url = backdrop.querySelector('#cu-url').value.trim();
    const title = backdrop.querySelector('#cu-title').value.trim();
    const tags = backdrop.querySelector('#cu-tags').value.split(',').map(s => s.trim()).filter(Boolean);
    const err = backdrop.querySelector('#cu-error');
    if (!url) { err.textContent = '请输入 URL'; err.classList.remove('hidden'); return; }
    const res = await apiPost('/knowledge/url', { url, title, tags });
    if (res.ok) { showToast('保存成功', 'success'); close(); window.location.hash = `#/knowledge/${res.data.data.id}`; }
    else { err.textContent = res.error || '保存失败'; err.classList.remove('hidden'); }
  });
}

export async function renderDetail(itemId) {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
      <div class="flex items-center gap-2 text-sm">
        <a href="#/knowledge" class="text-blue-600 hover:underline">← 返回知识库</a>
      </div>
      <div id="detail-content"></div>
    </div>
  `;
  const container = app.querySelector('#detail-content');
  renderSkeleton(container);
  const res = await apiGet(`/knowledge/${itemId}`);
  clearSkeleton(container);
  if (!res.ok) {
    container.innerHTML = `<div class="text-red-600">加载失败：${res.error}</div>`;
    return;
  }
  const item = res.data?.data;
  if (!item) {
    container.innerHTML = `<div class="text-red-600">知识不存在</div>`;
    return;
  }

  let isEditing = false;

  function renderView() {
    const contentText = item.current_version?.content_text || '';
    const tagsHtml = (item.tags || []).map(t => `<span class="inline-block mr-1 px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-xs">${t.name}</span>`).join('') || '<span class="text-gray-400 text-sm">无标签</span>';
    const attachmentsHtml = (item.attachments || []).map(a => `
      <li class="flex items-center justify-between bg-gray-50 dark:bg-gray-700 rounded px-3 py-2">
        <div class="text-sm truncate">${a.filename} <span class="text-xs text-gray-500">(${(a.size_bytes / 1024).toFixed(1)} KB)</span></div>
        <a href="/api/knowledge/${item.id}/attachments/${a.id}/download" target="_blank" class="text-blue-600 hover:underline text-sm">下载</a>
      </li>
    `).join('');
    const versionsHtml = (item.versions || []).map((v, idx) => `
      <li class="text-sm border-l-2 pl-3 ${idx === 0 ? 'border-blue-600' : 'border-gray-300 dark:border-gray-600'}">
        <div class="text-gray-500 text-xs">${fmtDate(v.created_at)} · ${v.created_by}</div>
        <div>${idx === 0 ? '当前版本' : '历史版本'}</div>
      </li>
    `).join('');

    container.innerHTML = `
      <div class="bg-white dark:bg-gray-800 rounded shadow p-4 space-y-4">
        <div class="flex items-start justify-between gap-2">
          <div>
            <h1 class="text-xl font-bold">${item.title || '无标题'}</h1>
            <div class="text-xs text-gray-500 mt-1">${item.source_type || ''} · 创建于 ${fmtDate(item.created_at)}</div>
          </div>
          <div class="flex gap-2 shrink-0">
            <button id="btn-edit" aria-label="编辑知识" class="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">编辑</button>
            <button id="btn-delete" aria-label="删除知识" class="px-3 py-1.5 rounded bg-red-100 text-red-700 hover:bg-red-200 text-sm ${item.is_deleted ? 'hidden' : ''}">删除</button>
          </div>
        </div>

        <div class="flex flex-wrap gap-2 items-center">
          ${tagsHtml}
        </div>

        <div class="prose dark:prose-invert max-w-none text-sm">
          ${renderMarkdown(contentText)}
        </div>

        ${attachmentsHtml ? `<div><h3 class="font-semibold text-sm mb-2">附件</h3><ul class="space-y-2">${attachmentsHtml}</ul></div>` : ''}

        ${item.confidence ? `<div class="bg-gray-50 dark:bg-gray-700 rounded p-3">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-sm font-medium">置信度</span>
            ${confidenceBadge(item.confidence.score_level)}
          </div>
          <div class="text-sm text-gray-600 dark:text-gray-300">${item.confidence.rationale || ''}</div>
          <div class="text-xs text-gray-400 mt-1">方法：${item.confidence.method || '-'} · ${fmtDate(item.confidence.evaluated_at)}</div>
        </div>` : ''}

        <div>
          <h3 class="font-semibold text-sm mb-2">版本历史</h3>
          <ul class="space-y-2">${versionsHtml || '<li class="text-sm text-gray-500">无版本记录</li>'}</ul>
        </div>
      </div>
    `;

    container.querySelector('#btn-edit').addEventListener('click', () => { isEditing = true; renderEdit(); });
    const delBtn = container.querySelector('#btn-delete');
    if (delBtn) delBtn.addEventListener('click', () => {
      showModal({
        title: '确认删除',
        body: '删除后该知识将被标记为已删除，是否继续？',
        actions: [
          { label: '取消', className: 'px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600' },
          { label: '删除', className: 'px-3 py-1.5 rounded bg-red-600 text-white hover:bg-red-700', onClick: async () => {
            const r = await apiDelete(`/knowledge/${item.id}`);
            if (r.ok) { showToast('已删除', 'success'); window.location.hash = '#/knowledge'; }
            else showToast(r.error || '删除失败', 'error');
          }}
        ]
      });
    });
  }

  function renderEdit() {
    const contentText = item.current_version?.content_text || '';
    const tagStr = (item.tags || []).map(t => t.name).join(', ');
    container.innerHTML = `
      <div class="bg-white dark:bg-gray-800 rounded shadow p-4 space-y-4">
        <h2 class="text-lg font-bold">编辑知识</h2>
        <div>
          <label class="block text-sm font-medium mb-1">标题</label>
          <input type="text" id="edit-title" value="${item.title || ''}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">内容</label>
          <textarea id="edit-content" rows="8" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm">${contentText}</textarea>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">标签（逗号分隔）</label>
          <input type="text" id="edit-tags" value="${tagStr}" class="w-full rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        </div>
        <div id="edit-error" class="text-red-600 text-sm hidden"></div>
        <div class="flex gap-2">
          <button id="edit-save" class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">保存</button>
          <button id="edit-cancel" class="px-4 py-2 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">取消</button>
        </div>
      </div>
    `;
    container.querySelector('#edit-cancel').addEventListener('click', () => { isEditing = false; renderView(); });
    container.querySelector('#edit-save').addEventListener('click', async () => {
      const title = container.querySelector('#edit-title').value.trim();
      const content = container.querySelector('#edit-content').value.trim();
      const tags = container.querySelector('#edit-tags').value.split(',').map(s => s.trim()).filter(Boolean);
      const err = container.querySelector('#edit-error');
      if (content.length < 5) { err.textContent = '内容长度必须 ≥5'; err.classList.remove('hidden'); return; }
      const payload = { title, content, tags };
      const r = await apiPatch(`/knowledge/${item.id}`, payload);
      if (r.ok) {
        showToast('保存成功', 'success');
        Object.assign(item, r.data.data);
        isEditing = false;
        renderView();
      } else {
        err.textContent = r.error || '保存失败';
        err.classList.remove('hidden');
      }
    });
  }

  renderView();
}
