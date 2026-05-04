// ── Bilingual support: English / German ──────────────────────────────────────

const TRANSLATIONS = {
  en: {
    // index.html
    'status.ready':        'Ready',
    'status.thinking':     'Thinking…',
    'welcome.title':       "Hello! I'm your AI Agent.",
    'welcome.subtitle':    "Ask me anything about the uploaded documents.",
    'input.placeholder':   'Ask a question…',

    // admin.html – login
    'login.title':         'Admin Login',
    'login.sub':           'AI Agent Document Manager',
    'login.username':      'Username',
    'login.password':      'Password',
    'login.btn':           'Login',

    // admin.html – panel
    'admin.title':         'Admin Panel',
    'admin.logout':        'Logout',
    'upload.heading':      'Upload Documents',
    'upload.formats':      'Supported formats: PDF, TXT, MD',
    'upload.dropzone':     'Drag & drop files here, or',
    'upload.browse':       'browse',
    'upload.btn':          'Upload',
    'docs.heading':        '📂 Uploaded Documents',
    'docs.refresh':        '↻ Refresh',
    'docs.empty':          'No uploads yet',
    'job.learning':        'AI learning…',
    'job.done':            'AI learned ✓',
    'job.error':           'Error',
    'job.delete':          'Delete',
  },
  de: {
    // index.html
    'status.ready':        'Bereit',
    'status.thinking':     'Verarbeitung…',
    'welcome.title':       'Hallo! Ich bin Ihr KI-Agent.',
    'welcome.subtitle':    'Stellen Sie mir Fragen zu den hochgeladenen Dokumenten.',
    'input.placeholder':   'Frage stellen…',

    // admin.html – login
    'login.title':         'Admin-Anmeldung',
    'login.sub':           'KI-Agent Dokumentenverwaltung',
    'login.username':      'Benutzername',
    'login.password':      'Passwort',
    'login.btn':           'Anmelden',

    // admin.html – panel
    'admin.title':         'Admin-Panel',
    'admin.logout':        'Abmelden',
    'upload.heading':      'Dokumente hochladen',
    'upload.formats':      'Unterstützte Formate: PDF, TXT, MD',
    'upload.dropzone':     'Dateien hierher ziehen oder',
    'upload.browse':       'durchsuchen',
    'upload.btn':          'Hochladen',
    'docs.heading':        '📂 Hochgeladene Dokumente',
    'docs.refresh':        '↻ Aktualisieren',
    'docs.empty':          'Noch keine Uploads',
    'job.learning':        'KI lernt…',
    'job.done':            'KI gelernt ✓',
    'job.error':           'Fehler',
    'job.delete':          'Löschen',
  },
};

// ── State ─────────────────────────────────────────────────────────────────────
let currentLang = localStorage.getItem('lang') || 'en';

// ── Public helpers ─────────────────────────────────────────────────────────────
function t(key) {
  return (TRANSLATIONS[currentLang] || TRANSLATIONS.en)[key] || key;
}

function applyTranslations() {
  // textContent
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  // placeholder
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  // Update toggle button label
  const btn = document.getElementById('langToggle');
  if (btn) btn.textContent = currentLang === 'en' ? 'DE' : 'EN';
}

function toggleLanguage() {
  currentLang = currentLang === 'en' ? 'de' : 'en';
  localStorage.setItem('lang', currentLang);
  applyTranslations();
}

// Auto-apply on load
document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
  const btn = document.getElementById('langToggle');
  if (btn) btn.addEventListener('click', toggleLanguage);
});
