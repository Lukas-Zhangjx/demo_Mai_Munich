const CONFIG = {
  apiUrl: 'https://demo-mai-munich.onrender.com',
  streamEnabled: true,
};

// Wrapper that injects ngrok bypass header on every request
function apiFetch(url, options = {}) {
  options.headers = {
    'ngrok-skip-browser-warning': '1',
    ...options.headers,
  };
  return fetch(url, options);
}

// ── State ──
const state = {
  conversationId: crypto.randomUUID(),
  pendingFiles: [],
  isLoading: false,
};

// ── DOM refs ──
const messagesEl   = document.getElementById('messages');
const inputEl      = document.getElementById('messageInput');
const sendBtn      = document.getElementById('sendBtn');
const fileInput    = document.getElementById('fileInput');
const filePreview  = document.getElementById('filePreview');
const statusDot    = document.getElementById('statusDot');
const statusText   = document.getElementById('statusText');

// ── Init ──
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

inputEl.addEventListener('input', () => autoResize(inputEl));

fileInput.addEventListener('change', () => {
  Array.from(fileInput.files).forEach(addFileTag);
  fileInput.value = '';
});

sendBtn.addEventListener('click', sendMessage);

checkBackendHealth();

// ── Core: send message ──
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || state.isLoading) return;

  clearWelcome();
  appendMessage('user', text, state.pendingFiles.map(f => f.name));

  inputEl.value = '';
  autoResize(inputEl);
  clearFileTags();
  setLoading(true);

  const thinkingEl = appendThinking();

  try {
    const formData = buildFormData(text);
    const response = await apiFetch(`${CONFIG.apiUrl}/api/chat`, {
      method: 'POST',
      body: formData,
    });

    thinkingEl.remove();

    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const contentType = response.headers.get('content-type') || '';
    if (CONFIG.streamEnabled && contentType.includes('text/event-stream')) {
      await handleStream(response);
    } else {
      const data = await response.json();
      handleJsonResponse(data);
    }
  } catch (err) {
    thinkingEl.remove();
    appendMessage('assistant', `Connection failed. Make sure the backend is running at ${CONFIG.apiUrl}`);
    setStatus('error', 'Disconnected');
  }

  setLoading(false);
}

// ── SSE streaming response ──
async function handleStream(response) {
  const reader  = response.body.getReader();
  const decoder = new TextDecoder();
  let   bubble  = null;
  let   buffer  = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (raw === '[DONE]') return;

      try {
        const event = JSON.parse(raw);
        bubble = processStreamEvent(event, bubble);
      } catch {
        // malformed chunk — skip
      }
    }
  }
}

function processStreamEvent(event, bubble) {
  if (event.type === 'tool_call') {
    appendToolCard(event.tool, event.input);
    return bubble;
  }

  if (event.type === 'tool_result') {
    updateLastToolCard(event.result);
    return bubble;
  }

  if (event.type === 'text') {
    if (!bubble) {
      bubble = createAssistantBubble();
    }
    bubble.textContent += event.content;
    scrollToBottom();
    return bubble;
  }

  return bubble;
}

// ── JSON (non-streaming) response ──
function handleJsonResponse(data) {
  if (data.tool_calls?.length) {
    data.tool_calls.forEach(tc => {
      appendToolCard(tc.name, tc.input);
      if (tc.result) updateLastToolCard(tc.result);
    });
  }
  if (data.message) {
    appendMessage('assistant', data.message);
  }
}

// ── DOM helpers ──
function appendMessage(role, text, fileNames = []) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.textContent = text;

  if (fileNames.length) {
    fileNames.forEach(name => {
      const tag = document.createElement('div');
      tag.className = 'file-tag';
      tag.textContent = `📎 ${name}`;
      bubble.appendChild(tag);
    });
  }

  const time = document.createElement('div');
  time.className = 'message-time';
  time.textContent = now();

  wrapper.appendChild(bubble);
  wrapper.appendChild(time);
  messagesEl.appendChild(wrapper);
  scrollToBottom();
  return bubble;
}

function createAssistantBubble() {
  const wrapper = document.createElement('div');
  wrapper.className = 'message assistant';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';

  const time = document.createElement('div');
  time.className = 'message-time';
  time.textContent = now();

  wrapper.appendChild(bubble);
  wrapper.appendChild(time);
  messagesEl.appendChild(wrapper);
  scrollToBottom();
  return bubble;
}

function appendThinking() {
  const el = document.createElement('div');
  el.className = 'thinking-indicator';
  el.innerHTML = `
    <div class="dots">
      <span></span><span></span><span></span>
    </div>
    <span>Agent is thinking…</span>
  `;
  messagesEl.appendChild(el);
  scrollToBottom();
  return el;
}

function appendToolCard(toolName, input) {
  const card = document.createElement('div');
  card.className = 'tool-card';
  card.innerHTML = `
    <div class="tool-card-header">
      <span>⚙</span>
      <span>Using tool:</span>
      <span class="tool-name">${escHtml(toolName)}</span>
    </div>
    <div class="tool-card-body">${escHtml(JSON.stringify(input, null, 2))}</div>
  `;
  messagesEl.appendChild(card);
  scrollToBottom();
  return card;
}

function updateLastToolCard(result) {
  const cards = messagesEl.querySelectorAll('.tool-card');
  const last  = cards[cards.length - 1];
  if (!last) return;

  const resultEl = document.createElement('div');
  resultEl.style.cssText = 'margin-top:6px; padding-top:6px; border-top:1px solid var(--border); color: var(--primary); font-family: monospace; font-size:12px;';
  resultEl.textContent = typeof result === 'string' ? result : JSON.stringify(result);
  last.appendChild(resultEl);
}

// ── File tags ──
function addFileTag(file) {
  state.pendingFiles.push(file);

  const tag = document.createElement('div');
  tag.className = 'file-tag';

  const name = document.createElement('span');
  name.textContent = `📎 ${file.name}`;

  const removeBtn = document.createElement('button');
  removeBtn.textContent = '×';
  removeBtn.onclick = () => {
    state.pendingFiles = state.pendingFiles.filter(f => f !== file);
    tag.remove();
  };

  tag.appendChild(name);
  tag.appendChild(removeBtn);
  filePreview.appendChild(tag);
}

function clearFileTags() {
  state.pendingFiles = [];
  filePreview.innerHTML = '';
}

// ── FormData builder ──
function buildFormData(text) {
  const fd = new FormData();
  fd.append('message', text);
  fd.append('conversation_id', state.conversationId);
  state.pendingFiles.forEach(f => fd.append('files', f));
  return fd;
}

// ── Backend health check ──
async function checkBackendHealth() {
  try {
    const res = await apiFetch(`${CONFIG.apiUrl}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      setStatus('ready', 'Connected');
    } else {
      setStatus('error', 'Backend error');
    }
  } catch {
    setStatus('error', 'No backend');
  }
}

// ── UI state ──
function setLoading(on) {
  state.isLoading = on;
  sendBtn.disabled = on;
  if (on) {
    setStatus('thinking', 'Thinking…');
  } else {
    setStatus('ready', 'Connected');
  }
}

function setStatus(type, label) {
  statusText.textContent = label;
  statusDot.className = 'status-dot' + (type !== 'ready' ? ` ${type}` : '');
}

function clearWelcome() {
  const w = messagesEl.querySelector('.welcome-card');
  if (w) w.remove();
}

function scrollToBottom() {
  const area = document.getElementById('chatArea');
  area.scrollTop = area.scrollHeight;
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
