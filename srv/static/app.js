// static/app.js
window.resetForms = function resetForms() {
  // limpia file input
  const f = document.getElementById('file');
  if (f) f.value = '';

  // limpia url
  const url = document.getElementById('urlInput');
  if (url) url.value = '';

  // restablece selects del bloque de descarga
  const kind = document.getElementById('dlKind');
  const q    = document.getElementById('dlQuality');
  if (kind) kind.value = 'video';

  // si la función fillQuality existe (está en tu <script> inline), recárgala
  if (typeof window.fillQuality === 'function') {
    window.fillQuality();
  }

  // calidad por defecto
  if (q) q.value = 'best';

  // limpia mensajes
  const s1 = document.getElementById('status');
  const s2 = document.getElementById('status2');
  if (s1) s1.textContent = '';
  if (s2) s2.textContent = '';
};

// ===== extra: Enter en campo URL dispara descarga =====
document.getElementById('urlInput')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault(); // evita recarga de página
    if (typeof window.startFetch === 'function') {
      window.startFetch();
    }
  }
});
