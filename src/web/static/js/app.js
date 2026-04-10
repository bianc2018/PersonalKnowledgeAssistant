import { initRouter } from './router.js';
import './store.js';
import './api.js';
import './ui.js';
import './sse.js';

window.pages = {};

document.addEventListener('DOMContentLoaded', () => {
  initRouter();
});
