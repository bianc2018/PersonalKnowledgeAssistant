export function createSSEStream(url, callbacks, token) {
  const abortController = new AbortController();
  let buffer = '';

  const start = async () => {
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(url, { headers, signal: abortController.signal });
      if (!res.body) throw new Error('No response body');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const payload = trimmed.slice(5).trim();
          if (!payload) continue;
          let data;
          try {
            data = JSON.parse(payload);
          } catch {
            data = { type: 'chunk', raw: payload };
          }
          const eventType = data.type || 'chunk';
          if (callbacks.onEvent) {
            callbacks.onEvent(eventType, data);
          }
          switch (eventType) {
            case 'delta':
              if (callbacks.onDelta) callbacks.onDelta(data);
              break;
            case 'citation':
              if (callbacks.onCitation) callbacks.onCitation(data);
              break;
            case 'done':
              if (callbacks.onDone) callbacks.onDone(data);
              break;
            case 'error':
              if (callbacks.onError) callbacks.onError(data);
              break;
            case 'status':
              if (callbacks.onStatus) callbacks.onStatus(data);
              break;
            case 'progress':
              if (callbacks.onProgress) callbacks.onProgress(data);
              break;
            case 'chunk':
              if (callbacks.onChunk) callbacks.onChunk(data);
              break;
            case 'question':
              if (callbacks.onQuestion) callbacks.onQuestion(data);
              break;
            case 'report':
              if (callbacks.onReport) callbacks.onReport(data);
              break;
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError' && callbacks.onError) {
        callbacks.onError({ type: 'error', message: err.message });
      }
    }
  };

  start();

  return {
    abort() {
      abortController.abort();
    }
  };
}
