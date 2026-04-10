import { apiGet, apiPost, apiPatch, apiDelete } from '../api.js';
import { createSSEStream } from '../sse.js';
import { renderMarkdown, showToast, showModal } from '../ui.js';
import { getToken } from '../store.js';

function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return isNaN(d) ? iso : `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

function renderCitations(citations) {
  if (!citations || !citations.length) return '';
  return `<div class="mt-2 flex flex-wrap gap-2">
    ${citations.map(c => `
      <a href="#/knowledge/${c.item_id}" class="inline-flex items-center gap-1 px-2 py-1 rounded bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-200 text-xs hover:underline" title="${c.item_title || ''}">
        <span>[${c.citation_index}]</span>
        <span class="truncate max-w-[12rem]">${c.item_title || '来源'}</span>
      </a>
    `).join('')}
  </div>`;
}

let currentConvId = null;
let currentStreamAbort = null;

export async function render(convId) {
  currentConvId = convId || null;
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="flex h-[calc(100vh-3.5rem)] md:h-screen">
      <!-- sidebar -->
      <div class="w-64 border-r bg-white dark:bg-gray-800 flex flex-col hidden md:flex">
        <div class="p-3 border-b dark:border-gray-700 flex items-center justify-between">
          <span class="font-semibold text-sm">会话</span>
          <button id="btn-new-conv" class="px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 text-xs">+ 新建</button>
        </div>
        <div id="conv-list" class="flex-1 overflow-y-auto p-2 space-y-1"></div>
      </div>

      <!-- main -->
      <div class="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
        <div class="md:hidden p-3 border-b bg-white dark:bg-gray-800 flex items-center justify-between">
          <span class="font-semibold text-sm">${convId ? '会话' : '选择或新建会话'}</span>
          <button id="btn-new-conv-mobile" class="px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 text-xs">+ 新建</button>
        </div>
        <div id="messages" class="flex-1 overflow-y-auto p-4 space-y-4" ${convId ? 'aria-live="polite"' : ''}></div>
        <div class="p-3 border-t bg-white dark:bg-gray-800">
          <form id="chat-form" class="flex gap-2">
            <input type="text" id="chat-input" class="flex-1 rounded border dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" placeholder="输入消息..." ${convId ? '' : 'disabled'} />
            <button type="submit" class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm" ${convId ? '' : 'disabled'}>发送</button>
          </form>
        </div>
      </div>
    </div>
  `;

  const listContainer = app.querySelector('#conv-list');
  const msgContainer = app.querySelector('#messages');

  async function loadConversations() {
    const res = await apiGet('/chat/conversations', { limit: 100 });
    const items = res.ok && res.data ? (res.data.data || []) : [];
    listContainer.innerHTML = items.map(c => `
      <div class="group flex items-center justify-between rounded px-2 py-2 text-sm cursor-pointer ${c.id === convId ? 'bg-gray-100 dark:bg-gray-700 font-medium' : 'hover:bg-gray-100 dark:hover:bg-gray-700'}">
        <a href="#/chat/${c.id}" class="flex-1 truncate">${c.title || '新会话'}</a>
        <div class="hidden group-hover:flex items-center gap-1">
          <button data-id="${c.id}" class="btn-rename text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" title="重命名">✎</button>
          <button data-id="${c.id}" class="btn-delete text-red-500 hover:text-red-700" title="删除">×</button>
        </div>
      </div>
    `).join('');

    listContainer.querySelectorAll('.btn-rename').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        const id = btn.dataset.id;
        const newTitle = prompt('新会话名称');
        if (!newTitle) return;
        const r = await apiPatch(`/chat/conversations/${id}`, { title: newTitle.trim() });
        if (r.ok) { showToast('重命名成功', 'success'); loadConversations(); }
        else showToast(r.error || '重命名失败', 'error');
      });
    });

    listContainer.querySelectorAll('.btn-delete').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        const id = btn.dataset.id;
        showModal({
          title: '确认删除',
          body: '删除后该会话的所有消息将被清空，是否继续？',
          actions: [
            { label: '取消', className: 'px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600' },
            { label: '删除', className: 'px-3 py-1.5 rounded bg-red-600 text-white hover:bg-red-700', onClick: async () => {
              const r = await apiDelete(`/chat/conversations/${id}`);
              if (r.ok) { showToast('已删除', 'success'); if (convId === id) { window.location.hash = '#/chat'; } else { loadConversations(); } }
              else showToast(r.error || '删除失败', 'error');
            }}
          ]
        });
      });
    });
  }

  async function loadMessages() {
    if (!convId) {
      msgContainer.innerHTML = `<div class="text-center text-gray-500 text-sm mt-10">请从左侧选择一个会话，或点击“新建”开始聊天</div>`;
      return;
    }
    msgContainer.innerHTML = '';
    const res = await apiGet(`/chat/conversations/${convId}/messages`);
    if (!res.ok) {
      msgContainer.innerHTML = `<div class="text-red-600 text-sm">加载消息失败</div>`;
      return;
    }
    const msgs = res.data?.data || [];
    msgs.forEach(m => appendMessage(m));
    scrollToBottom();
  }

  function appendMessage(msg, placeholder=false) {
    const isUser = msg.role === 'user';
    const el = document.createElement('div');
    el.className = `flex ${isUser ? 'justify-end' : 'justify-start'}`;
    el.innerHTML = `
      <div class="max-w-[85%] md:max-w-[70%] rounded-lg px-4 py-2 text-sm ${isUser ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800 border dark:border-gray-700'}">
        <div class="prose dark:prose-invert max-w-none text-sm">${isUser ? escapeHtml(msg.content) : renderMarkdown(msg.content)}</div>
        ${renderCitations(msg.citations)}
      </div>
    `;
    msgContainer.appendChild(el);
    if (!placeholder) scrollToBottom();
    return el;
  }

  function scrollToBottom() {
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  app.querySelector('#btn-new-conv').addEventListener('click', () => { window.location.hash = '#/chat'; });
  const mobileNew = app.querySelector('#btn-new-conv-mobile');
  if (mobileNew) mobileNew.addEventListener('click', () => { window.location.hash = '#/chat'; });

  const form = app.querySelector('#chat-form');
  const input = app.querySelector('#chat-input');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    let targetId = convId;
    if (!targetId) {
      const r = await apiPost('/chat/conversations');
      if (r.ok && r.data && r.data.id) {
        targetId = r.data.id;
      } else {
        showToast('创建会话失败', 'error');
        return;
      }
    }

    // If we just created a new conv, redirect to it so the UI updates
    if (!convId) {
      window.location.hash = `#/chat/${targetId}`;
      return;
    }

    input.value = '';
    appendMessage({ role: 'user', content: text });

    const assistantEl = appendMessage({ role: 'assistant', content: '' }, true);
    const contentDiv = assistantEl.querySelector('.prose');
    let citations = [];

    if (currentStreamAbort) currentStreamAbort.abort();
    const token = getToken();
    const stream = createSSEStream(`/api/chat/conversations/${targetId}/messages`, {
      onDelta: (data) => {
        if (data.delta) {
          contentDiv.innerHTML = renderMarkdown(contentDiv.textContent + data.delta);
          scrollToBottom();
        }
      },
      onCitation: (data) => {
        if (data.citations) {
          citations = citations.concat(data.citations);
          const existing = assistantEl.querySelector('.citations-wrap');
          if (existing) existing.remove();
          const wrap = document.createElement('div');
          wrap.className = 'citations-wrap';
          wrap.innerHTML = renderCitations(citations);
          assistantEl.firstElementChild.appendChild(wrap);
          scrollToBottom();
        }
      },
      onError: (data) => {
        showToast(data.message || '流式响应出错', 'error');
      },
      onDone: () => {
        currentStreamAbort = null;
      }
    }, token);
    currentStreamAbort = stream;

    // send the POST
    const sendRes = await apiPost(`/chat/conversations/${targetId}/messages`, { content: text, stream: true });
    if (!sendRes.ok) {
      contentDiv.innerHTML = `<span class="text-red-600">发送失败：${sendRes.error}</span>`;
      if (currentStreamAbort) { currentStreamAbort.abort(); currentStreamAbort = null; }
    }
  });

  await loadConversations();
  await loadMessages();
  if (convId) input.focus();
}
