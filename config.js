// ── API configuration ──────────────────────────────────────────────────────
// Do NOT hard-code real URLs here — set the backend URL via the Admin Panel
// (Settings section) and it will be saved to localStorage automatically.
//
// Fallback order:
//   1. localStorage 'api_base'  ← set via Admin Panel → Settings
//   2. http://localhost:8000    ← default for local development

const API_BASE = localStorage.getItem('api_base') || 'http://localhost:8000';
