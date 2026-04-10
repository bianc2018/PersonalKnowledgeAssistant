import { apiGet } from '../api.js';
import { renderSkeleton, clearSkeleton } from '../ui.js';

export async function render() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
      <h1 class="text-2xl font-bold">Dashboard</h1>
      <div id="dash-content"></div>
    </div>
  `;
  const container = app.querySelector('#dash-content');
  renderSkeleton(container);

  const [statusRes, knowRes, chatRes] = await Promise.all([
    apiGet('/system/status'),
    apiGet('/knowledge', { limit: 5 }),
    apiGet('/chat/conversations', { limit: 3 }),
  ]);

  clearSkeleton(container);

  if (!statusRes.ok) {
    container.innerHTML = `<div class="text-red-600">加载失败</div>`;
    return;
  }

  const s = statusRes.data || {};
  const knowItems = knowRes.ok && knowRes.data ? (knowRes.data.data || []) : [];
  const convItems = chatRes.ok && chatRes.data ? (chatRes.data.data || []) : [];

  container.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-white dark:bg-gray-800 rounded shadow p-4">
        <div class="text-sm text-gray-500">知识条目</div>
        <div class="text-2xl font-bold">${s.knowledge_count ?? 0}</div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded shadow p-4">
        <div class="text-sm text-gray-500">LLM 状态</div>
        <div class="text-2xl font-bold">${s.llm_connected ? '已连接' : '未配置'}</div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded shadow p-4">
        <div class="text-sm text-gray-500">Embedding</div>
        <div class="text-2xl font-bold">${s.embedding_available ? '可用' : '未配置'}</div>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 rounded shadow p-4">
      <h2 class="font-semibold mb-3">快捷操作</h2>
      <div class="flex flex-wrap gap-2">
        <a href="#/knowledge" class="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">+ 新建知识</a>
        <a href="#/chat" class="px-3 py-2 rounded bg-green-600 text-white hover:bg-green-700 text-sm">+ 新会话</a>
        <a href="#/research" class="px-3 py-2 rounded bg-purple-600 text-white hover:bg-purple-700 text-sm">+ 开始调研</a>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="bg-white dark:bg-gray-800 rounded shadow p-4">
        <h2 class="font-semibold mb-3">最近知识</h2>
        ${knowItems.length ? `<ul class="space-y-2">
          ${knowItems.map(k => `<li>
            <a href="#/knowledge/${k.id}" class="text-blue-600 hover:underline text-sm">${k.title || '无标题'}</a>
            <div class="text-xs text-gray-500">${k.source_type || ''} · ${(k.tags || []).map(t => t.name).join(', ')}</div>
          </li>`).join('')}
        </ul>` : '<div class="text-gray-500 text-sm">暂无知识</div>'}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded shadow p-4">
        <h2 class="font-semibold mb-3">最近会话</h2>
        ${convItems.length ? `<ul class="space-y-2">
          ${convItems.map(c => `<li>
            <a href="#/chat/${c.id}" class="text-blue-600 hover:underline text-sm">${c.title || '新会话'}</a>
            <div class="text-xs text-gray-500">${c.message_count || 0} 条消息</div>
          </li>`).join('')}
        </ul>` : '<div class="text-gray-500 text-sm">暂无会话</div>'}
      </div>
    </div>
  `;
}
