(() => {
  const root = document.documentElement;
  const button = document.getElementById('themego') || document.getElementById('theme-toggle');
  const current = document.getElementById('themenow');
  let theme = 'light';
  try { theme = localStorage.getItem('cib-theme') || 'light'; } catch { root.dataset.storage = 'unavailable'; }
  function applyTheme() {
    root.dataset.theme = theme === 'dark' ? 'dark' : 'light';
    if (current) current.textContent = root.dataset.theme === 'dark' ? 'Dark' : 'Light';
    if (button) {
      button.textContent = root.dataset.theme === 'dark' ? 'Light' : 'Dark';
      button.setAttribute('aria-label', root.dataset.theme === 'dark' ? 'Use light theme' : 'Use dark theme');
    }
  }
  applyTheme();
  if (button) button.addEventListener('click', event => {
    event.stopImmediatePropagation();
    theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('cib-theme', theme); } catch { root.dataset.storage = 'unavailable'; }
    applyTheme();
  }, true);
  const dialog = document.createElement('dialog');
  dialog.className = 'diagram-dialog';
  dialog.setAttribute('aria-label', 'Expanded interactive diagram');
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'diagram-close';
  close.textContent = 'Close diagram';
  const contents = document.createElement('div');
  dialog.append(close, contents);
  document.body.append(dialog);
  let activeFigure;
  let placeholder;
  let opener;
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => {
    if (activeFigure && placeholder) {
      placeholder.replaceWith(activeFigure);
      opener.hidden = false;
      opener.focus();
    }
    activeFigure = undefined;
    placeholder = undefined;
  });
  document.querySelectorAll('figure').forEach(figure => {
    if (!figure.querySelector('svg') || figure.classList.contains('lab')) return;
    const expand = document.createElement('button');
    expand.type = 'button';
    expand.className = 'expand-diagram';
    expand.textContent = root.lang === 'ar' ? 'تكبير الرسم' : 'Enlarge diagram';
    if (root.lang === 'ar') close.textContent = 'إغلاق الرسم';
    expand.addEventListener('click', () => {
      activeFigure = figure;
      opener = expand;
      placeholder = document.createElement('div');
      placeholder.style.height = `${figure.getBoundingClientRect().height}px`;
      figure.replaceWith(placeholder);
      contents.append(figure);
      expand.hidden = true;
      dialog.showModal();
      close.focus();
    });
    figure.append(expand);
  });
  document.querySelectorAll('.rail a[href^="#"]').forEach(link => {
    if (!link.getAttribute('aria-label')) link.setAttribute('aria-label', link.textContent.trim());
  });
})();
