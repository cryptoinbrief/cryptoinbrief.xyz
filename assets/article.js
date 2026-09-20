(() => {
  const root = document.documentElement;
  const button = document.getElementById('themego') || document.getElementById('theme-toggle');
  const arabic = root.lang === 'ar';
  if (button?.parentElement.classList.contains('theme')) button.parentElement.replaceChildren(button);
  document.querySelectorAll('.site-header .lang').forEach(language => {
    [...language.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).forEach(node => node.remove());
  });
  let theme = 'light';
  try { theme = localStorage.getItem('cib-theme') || 'light'; } catch { root.dataset.storage = 'unavailable'; }
  function applyTheme() {
    root.dataset.theme = theme === 'dark' ? 'dark' : 'light';
    if (button) {
      const dark = root.dataset.theme === 'dark';
      const label = arabic ? (dark ? 'استخدم الوضع الفاتح' : 'استخدم الوضع الداكن') : (dark ? 'Use light theme' : 'Use dark theme');
      button.innerHTML = dark
        ? '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
        : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.7 13.1A9 9 0 0 1 10.9 3.3 9 9 0 1 0 20.7 13.1Z"/></svg>';
      button.classList.add('article-theme-button');
      button.setAttribute('aria-label', label);
      button.title = label;
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
