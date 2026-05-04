const API = typeof API_BASE !== 'undefined' ? API_BASE : 'https://demo-mai-munich.onrender.com';
const TOKEN_KEY = 'admin_token';

// Wrapper that injects ngrok bypass header on every request
function apiFetch(url, options = {}) {
  options.headers = {
    'ngrok-skip-browser-warning': '1',
    ...options.headers,
  };
  return fetch(url, options);
}

// ── DOM refs ──
const loginOverlay = document.getElementById('loginOverlay');
const adminApp     = document.getElementById('adminApp');
const loginForm    = document.getElementById('loginForm');
const loginError   = document.getElementById('loginError');
const loginBtn     = document.getElementById('loginBtn');
const logoutBtn    = document.getElementById('logoutBtn');
const dropZone     = document.getElementById('dropZone');
const browseLink   = document.getElementById('browseLink');
const fileInput    = document.getElementById('fileInput');
const uploadQueue  = document.getElementById('uploadQueue');
const uploadBtn    = document.getElementById('uploadBtn');
const refreshBtn   = document.getElementById('refreshBtn');

let pendingFiles = [];

// ── Init ──
if (getToken()) {
  showApp();
  loadJobs();
  setInterval(loadJobs, 8000);  // auto-refresh job status every 8s
}

// ── Login ──
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.textContent = '';
  loginBtn.disabled = true;
  loginBtn.textContent = 'Logging in…';

  try {
    const res = await apiFetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
      }),
    });

    if (!res.ok) {
      loginError.textContent = 'Invalid username or password.';
      return;
    }

    const { token } = await res.json();
    setToken(token);
    showApp();
    loadDocuments();
  } catch {
    loginError.textContent = 'Cannot connect to backend.';
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = 'Login';
  }
});

logoutBtn.addEventListener('click', () => {
  clearToken();
  location.reload();
});

// ── File selection ──
browseLink.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => addFiles(Array.from(fileInput.files)));

dropZone.addEventListener('dragover',  (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', ()  => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  addFiles(Array.from(e.dataTransfer.files));
});

function addFiles(files) {
  files.forEach(file => {
    if (pendingFiles.find(f => f.name === file.name)) return;
    pendingFiles.push(file);
    renderQueueItem(file);
  });
  uploadBtn.disabled = pendingFiles.length === 0;
}

function renderQueueItem(file) {
  const item = document.createElement('div');
  item.className = 'queue-item';
  item.id = `queue-${file.name}`;
  item.innerHTML = `
    <div class="queue-item-name">📄 <span>${file.name}</span></div>
    <span class="queue-item-status" id="status-${file.name}">Ready</span>
  `;
  uploadQueue.appendChild(item);
}

// ── Upload ──
uploadBtn.addEventListener('click', async () => {
  if (!pendingFiles.length) return;
  uploadBtn.disabled = true;

  for (const file of pendingFiles) {
    setQueueStatus(file.name, 'Uploading…', '');
    const fd = new FormData();
    fd.append('files', file);

    try {
      const res = await apiFetch(`${API}/api/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      });

      if (res.status === 401) { handleUnauthorized(); return; }

      const data = await res.json();
      const result = data.results?.[0];

      if (result?.status === 'processing') {
        setQueueStatus(file.name, '✓ 已接收，AI 正在学习中…', 'success');
      } else if (result?.status === 'ok') {
        setQueueStatus(file.name, `✓ ${result.chunks} chunks`, 'success');
      } else {
        setQueueStatus(file.name, result?.status || 'Error', 'error');
      }
    } catch {
      setQueueStatus(file.name, 'Upload failed', 'error');
    }
  }

  pendingFiles = [];
  uploadBtn.disabled = true;
  fileInput.value = '';
  loadJobs();
});

function setQueueStatus(filename, text, cls) {
  const el = document.getElementById(`status-${filename}`);
  if (!el) return;
  el.textContent = text;
  el.className = `queue-item-status ${cls}`;
}

// ── Refresh button ──
refreshBtn.addEventListener('click', loadJobs);

async function deleteDocument(filename) {
  if (!confirm(`Delete "${filename}" and all its chunks?`)) return;

  const el = document.getElementById(`doc-${filename}`);
  if (el) el.style.opacity = '0.5';

  try {
    const res = await apiFetch(`${API}/api/documents/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    });

    if (res.status === 401) { handleUnauthorized(); return; }
    loadDocuments();
  } catch {
    alert('Delete failed. Please try again.');
    if (el) el.style.opacity = '1';
  }
}

// ── Document list (upload_jobs as source of truth) ──
async function loadJobs() {
  const jobList = document.getElementById('jobList');
  if (!jobList) return;

  try {
    const res = await apiFetch(`${API}/api/upload-jobs`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) return;

    const { jobs } = await res.json();
    if (!jobs.length) {
      jobList.innerHTML = '<div class="empty-state">暂无上传记录</div>';
      return;
    }

    jobList.innerHTML = '';
    jobs.forEach(job => {
      const item = document.createElement('div');
      item.className = 'doc-item';

      const statusBadge = job.status === 'done'
        ? '<span style="color:#16a34a;font-weight:600">✅ AI 已学习</span>'
        : job.status === 'error'
        ? '<span style="color:#dc2626;font-weight:600">❌ 处理失败</span>'
        : '<span style="color:#d97706;font-weight:600">🔄 AI 正在学习中…</span>';

      const meta = job.status === 'done'
        ? `${job.chunks} chunks · ${new Date(job.created_at).toLocaleString()}`
        : new Date(job.created_at).toLocaleString();

      item.innerHTML = `
        <div class="doc-info">
          <span class="doc-name">📄 ${job.filename}</span>
          <span class="doc-meta">${meta}</span>
        </div>
        <div class="doc-actions">
          ${statusBadge}
        </div>`;
      jobList.appendChild(item);
    });
  } catch {
    // silently ignore
  }
}

// ── Auth helpers ──
function showApp() {
  loginOverlay.style.display = 'none';
  adminApp.style.display = 'flex';
  adminApp.style.flexDirection = 'column';
}

function handleUnauthorized() {
  clearToken();
  alert('Session expired. Please log in again.');
  location.reload();
}

function getToken()      { return localStorage.getItem(TOKEN_KEY); }
function setToken(t)     { localStorage.setItem(TOKEN_KEY, t); }
function clearToken()    { localStorage.removeItem(TOKEN_KEY); }
