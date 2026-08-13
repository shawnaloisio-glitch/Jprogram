// Jprogram Web UI — shared dark/light toggle.
// Default: follows the OS/browser preference live (prefers-color-scheme).
// A click sets an explicit override, persisted in localStorage, until toggled back.
(function () {
  const STORAGE_KEY = 'jprogram-theme';
  const root = document.documentElement;
  const media = window.matchMedia('(prefers-color-scheme: dark)');

  function storedTheme() {
    return localStorage.getItem(STORAGE_KEY);
  }

  function systemTheme() {
    return media.matches ? 'dark' : 'light';
  }

  function effectiveTheme() {
    return storedTheme() || systemTheme();
  }

  function updateButton(btn, theme) {
    btn.textContent = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
  }

  function applyAndSync(btn) {
    const s = storedTheme();
    if (s) {
      root.setAttribute('data-theme', s);
    } else {
      root.removeAttribute('data-theme');
    }
    updateButton(btn, effectiveTheme());
  }

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    applyAndSync(btn);
    btn.addEventListener('click', () => {
      const next = effectiveTheme() === 'dark' ? 'light' : 'dark';
      localStorage.setItem(STORAGE_KEY, next);
      applyAndSync(btn);
    });
    media.addEventListener('change', () => {
      if (!storedTheme()) applyAndSync(btn);
    });
  });
})();
