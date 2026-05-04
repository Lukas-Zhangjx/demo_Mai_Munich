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
  loginBtn.textContent = t('login.btn') + '…';

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
      loginError.textContent = currentLang === 'de'
        ? 'Ungültiger Benutzername oder Passwort.'
        : 'Invalid username or password.';
      return;
    }

    const { token } = await res.json();
    setToken(token);
    showApp();
    loadJobs();
    setInterval(loadJobs, 8000);
  } catch {
    loginError.textContent = currentLang === 'de'
      ? 'Keine Verbindung zum Backend.'
      : 'Cannot connect to backend.';
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = t('login.btn');
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
    <span class="queue-item-status" id="status-${file.name}">${t('status.ready')}</span>
  `;
  uploadQueue.appendChild(item);
}

// ── Upload ──
uploadBtn.addEventListener('click', async () => {
  if (!pendingFiles.length) return;
  uploadBtn.disabled = true;

  for (const file of pendingFiles) {
    setQueueStatus(file.name, currentLang === 'de' ? 'Wird hochgeladen…' : 'Uploading…', '');
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
        setQueueStatus(file.name, '✓ ' + t('job.learning'), 'success');
      } else if (result?.status === 'ok') {
        setQueueStatus(file.name, `✓ ${result.chunks} chunks`, 'success');
      } else {
        setQueueStatus(file.name, result?.status || t('job.error'), 'error');
      }
    } catch {
      setQueueStatus(file.name, currentLang === 'de' ? 'Upload fehlgeschlagen' : 'Upload failed', 'error');
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

// ── Delete job ──
async function deleteJob(jobId, filename) {
  const msg = currentLang === 'de'
    ? `"${filename}" und alle zugehörigen Daten löschen?`
    : `Delete "${filename}" and all its data?`;
  if (!confirm(msg)) return;
  try {
    await apiFetch(`${API}/api/upload-jobs/${jobId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    loadJobs();
  } catch {
    alert(currentLang === 'de' ? 'Löschen fehlgeschlagen' : 'Delete failed');
  }
}

// ── Refresh button ──
refreshBtn.addEventListener('click', loadJobs);

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
      jobList.innerHTML = `<div class="empty-state">${t('docs.empty')}</div>`;
      return;
    }

    jobList.innerHTML = '';
    jobs.forEach(job => {
      const item = document.createElement('div');
      item.className = 'doc-item';

      const statusBadge = job.status === 'done'
        ? `<span style="color:#16a34a;font-weight:600">✅ ${t('job.done')}</span>`
        : job.status === 'error'
        ? `<span style="color:#dc2626;font-weight:600">❌ ${t('job.error')}</span>`
        : `<span style="color:#d97706;font-weight:600">🔄 ${t('job.learning')}</span>`;

      const meta = job.status === 'done'
        ? `${job.chunks} chunks · ${new Date(job.created_at).toLocaleString()}`
        : new Date(job.created_at).toLocaleString();

      item.innerHTML = `
        <div class="doc-info">
          <span class="doc-name">📄 ${job.filename}</span>
          <span class="doc-meta">${meta}</span>
        </div>
        <div class="doc-actions" style="display:flex;align-items:center;gap:12px;">
          ${statusBadge}
          <button class="btn-danger" data-id="${job.id}">${t('job.delete')}</button>
        </div>`;
      item.querySelector('.btn-danger').addEventListener('click', () => deleteJob(job.id, job.filename));
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
  alert(currentLang === 'de' ? 'Sitzung abgelaufen. Bitte erneut anmelden.' : 'Session expired. Please log in again.');
  location.reload();
}

function getToken()      { return localStorage.getItem(TOKEN_KEY); }
function setToken(tk)    { localStorage.setItem(TOKEN_KEY, tk); }
function clearToken()    { localStorage.removeItem(TOKEN_KEY); }
