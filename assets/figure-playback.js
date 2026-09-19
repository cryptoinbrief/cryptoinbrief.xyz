(function () {
  'use strict';

  var root = document.documentElement;
  var rtl = root.dir === 'rtl' || root.lang === 'ar';
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var labels = rtl ? {
    lesson: 'شرح بصري تلقائي',
    playing: 'يعمل تلقائيا',
    paused: 'متوقف مؤقتا',
    play: 'تشغيل',
    pause: 'إيقاف مؤقت',
    step: 'خطوة'
  } : {
    lesson: 'Automatic visual lesson',
    playing: 'Playing automatically',
    paused: 'Paused',
    play: 'Play',
    pause: 'Pause',
    step: 'Step'
  };

  var coin = location.pathname.toLowerCase().indexOf('zero-knowledge') >= 0 ? 'zk' : (root.getAttribute('data-coin') || coinFromPath());
  var coinData = {
    bitcoin: ['Bitcoin', 'assets/coins/bitcoin.svg'],
    ethereum: ['Ethereum', 'assets/coins/ethereum.svg'],
    monero: ['Monero', 'assets/coins/monero.svg'],
    solana: ['Solana', 'assets/coins/solana.svg'],
    sui: ['Sui', 'assets/coins/sui.svg'],
    zcash: ['Zcash', 'assets/coins/zcash.svg']
  };
  var figures = [];
  var visible = new Map();
  var active = null;
  var observer = null;

  function coinFromPath() {
    var p = location.pathname.toLowerCase();
    if (p.indexOf('bitcoin') >= 0) return 'bitcoin';
    if (p.indexOf('monero') >= 0) return 'monero';
    if (p.indexOf('solana') >= 0) return 'solana';
    if (p.indexOf('sui') >= 0) return 'sui';
    if (p.indexOf('zcash') >= 0) return 'zcash';
    if (p.indexOf('proof-of-stake') >= 0) return 'ethereum';
    return 'overview';
  }

  function make(tag, className, text) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    if (text != null) el.textContent = text;
    return el;
  }

  function compact(text, max) {
    var value = (text || '').replace(/\s+/g, ' ').trim();
    if (value.length <= max) return value;
    return value.slice(0, max).replace(/\s+\S*$/, '') + '…';
  }

  function figureTitle(fig, index) {
    var cap = fig.querySelector('figcaption');
    var number = cap && cap.querySelector('.figno');
    if (number && number.textContent.trim()) return number.textContent.trim();
    return labels.step + ' ' + (index + 1);
  }

  function figureCaption(fig) {
    var cap = fig.querySelector('figcaption');
    if (!cap) return '';
    var copy = cap.cloneNode(true);
    var number = copy.querySelector('.figno');
    if (number) number.remove();
    return compact(copy.textContent, 150);
  }

  function appendLogo(target) {
    var data = coinData[coin];
    if (data) {
      var img = make('img', 'fp-logo');
      img.src = data[1];
      img.alt = '';
      img.width = 30;
      img.height = 30;
      target.appendChild(img);
      return data[0];
    }
    if (coin === 'overview') {
      var group = make('span', 'fp-logo-group');
      ['bitcoin', 'ethereum', 'solana', 'monero', 'zcash'].forEach(function (name) {
        var item = make('img', 'fp-logo');
        item.src = coinData[name][1];
        item.alt = '';
        item.width = 24;
        item.height = 24;
        group.appendChild(item);
      });
      target.appendChild(group);
      return rtl ? 'أساسيات العملات المشفرة' : 'Crypto fundamentals';
    }
    var mark = make('span', 'fp-concept-mark', 'ZK');
    target.appendChild(mark);
    return rtl ? 'شرح التشفير' : 'Cryptography explained';
  }

  function semanticSteps(fig) {
    var svg = fig.querySelector('svg');
    if (!svg) return [];
    var found = [];
    var seen = Object.create(null);
    Array.prototype.forEach.call(svg.querySelectorAll('[data-step]'), function (el) {
      var key = el.getAttribute('data-step') || String(found.length + 1);
      if (seen[key]) return;
      seen[key] = true;
      var note = el.getAttribute('data-note');
      if (!note) {
        var peer = svg.querySelector('[data-step="' + CSS.escape(key) + '"][data-note]');
        note = peer && peer.getAttribute('data-note');
      }
      found.push({ key: key, note: compact(note, 190), el: el });
    });
    if (found.length) return found;
    Array.prototype.forEach.call(svg.querySelectorAll('[data-note]'), function (el) {
      var note = compact(el.getAttribute('data-note'), 190);
      if (note && found.length < 8) found.push({ key: String(found.length + 1), note: note, el: el });
    });
    return found;
  }

  function nativeControls(fig) {
    return Array.prototype.slice.call(fig.querySelectorAll('.figctl button, .figui button, .fx-strip button, button.figbtn, [data-act]')).filter(function (button) {
      return !button.closest('.fp-control');
    });
  }

  function controlByRole(fig, role) {
    var buttons = nativeControls(fig);
    var expressions = {
      replay: /replay|restart|reset|إعادة|ابدأ|تشغيل من/i,
      next: /next|step|toggle|show|view|before|after|generate|verify|lane|cadence|finality|خطوة|التالي|اعرض|إجباري|اختياري|البروتوكول|المنصة/i
    };
    for (var i = 0; i < buttons.length; i++) {
      var action = buttons[i].getAttribute('data-act') || '';
      if (role === 'replay' && action === 'replay') return buttons[i];
      if (role === 'next' && (action === 'step' || action === 'toggle')) return buttons[i];
      if (expressions[role].test(buttons[i].textContent || '')) return buttons[i];
    }
    return null;
  }

  function setNarrative(state, text, manual) {
    var value = compact(text || state.caption, 190);
    if (!value) return;
    state.narrative.textContent = value;
    state.narrative.setAttribute('aria-live', manual ? 'polite' : 'off');
    if (manual) {
      clearTimeout(state.liveTimer);
      state.liveTimer = setTimeout(function () {
        state.narrative.setAttribute('aria-live', 'off');
      }, 900);
    }
  }

  function setPlaying(state, playing) {
    state.playing = playing;
    state.figure.classList.toggle('fp-playing', playing);
    state.figure.classList.toggle('fp-paused', !playing);
    state.button.textContent = playing ? labels.pause : labels.play;
    state.button.setAttribute('aria-label', playing ? labels.pause : labels.play);
    state.button.setAttribute('aria-pressed', playing ? 'false' : 'true');
    state.status.textContent = playing ? labels.playing : labels.paused;
  }

  function clearSchedule(state) {
    clearTimeout(state.timer);
    clearTimeout(state.replayTimer);
    clearInterval(state.guardTimer);
    state.timer = 0;
    state.replayTimer = 0;
    state.guardTimer = 0;
  }

  function haltNative(state) {
    clearInterval(state.figure._ai);
    clearTimeout(state.figure._at);
    clearTimeout(state.figure._fxAuto);
    if (state.figure._figsteps && state.figure._figsteps.halt) state.figure._figsteps.halt();
  }

  function highlight(state, step) {
    state.steps.forEach(function (item) {
      item.el.classList.toggle('fp-muted', !!step && item !== step);
    });
    if (state.highlighted) state.highlighted.classList.remove('fp-focus');
    state.highlighted = step && step.el;
    if (state.highlighted) state.highlighted.classList.add('fp-focus');
  }

  function clickNative(state, button) {
    state.internalClicks++;
    button.click();
    state.internalClicks--;
  }

  function advance(state) {
    if (!state.playing || active !== state || document.hidden) return;
    haltNative(state);
    var next = controlByRole(state.figure, 'next');
    if (next && !next.disabled) clickNative(state, next);
    if (state.steps.length) {
      state.stepIndex = (state.stepIndex + 1) % state.steps.length;
      var step = state.steps[state.stepIndex];
      highlight(state, step);
      setNarrative(state, step.note || state.caption, false);
      state.progress.style.setProperty('--fp-progress', ((state.stepIndex + 1) / state.steps.length * 100) + '%');
      state.counter.textContent = (state.stepIndex + 1) + ' / ' + state.steps.length;
    } else {
      state.stepIndex++;
      state.progress.style.setProperty('--fp-progress', ((state.stepIndex % 4 + 1) / 4 * 100) + '%');
    }
    state.timer = setTimeout(function () { advance(state); }, 3600);
  }

  function start(state, manual) {
    if (document.hidden || !visible.has(state.figure)) return;
    if (active && active !== state) stop(active, false);
    active = state;
    state.userPaused = false;
    state.stepIndex = -1;
    clearSchedule(state);
    haltNative(state);
    highlight(state, null);
    setPlaying(state, true);
    setNarrative(state, state.caption, manual);
    state.progress.style.setProperty('--fp-progress', '0%');
    var replay = controlByRole(state.figure, 'replay');
    if (!reduced && replay && !replay.disabled) clickNative(state, replay);
    state.guardTimer = setInterval(function () { haltNative(state); }, 220);
    state.replayTimer = setTimeout(function () { advance(state); }, reduced ? 180 : 1700);
  }

  function stop(state, user) {
    clearSchedule(state);
    haltNative(state);
    setPlaying(state, false);
    if (user) state.userPaused = true;
    if (active === state) active = null;
  }

  function chooseActive() {
    if (document.hidden) {
      if (active) stop(active, false);
      return;
    }
    var candidates = figures.filter(function (state) {
      return visible.has(state.figure) && !state.userPaused;
    });
    if (!candidates.length) {
      if (active) stop(active, false);
      return;
    }
    candidates.sort(function (a, b) {
      var ar = a.figure.getBoundingClientRect();
      var br = b.figure.getBoundingClientRect();
      var ac = Math.abs((ar.top + ar.bottom) / 2 - innerHeight / 2);
      var bc = Math.abs((br.top + br.bottom) / 2 - innerHeight / 2);
      return ac - bc;
    });
    var chosen = candidates[0];
    if (active !== chosen) start(chosen, false);
  }

  function mount(fig, index) {
    if (fig.dataset.figurePlayback === 'ready' || !fig.querySelector('svg')) return null;
    fig.dataset.figurePlayback = 'ready';
    var top = make('div', 'fp-topline');
    var identity = make('div', 'fp-identity');
    var brand = make('span', 'fp-brand');
    var coinName = appendLogo(brand);
    var copy = make('span', 'fp-heading');
    copy.appendChild(make('strong', '', figureTitle(fig, index)));
    copy.appendChild(make('span', '', coinName + ' · ' + labels.lesson));
    identity.appendChild(brand);
    identity.appendChild(copy);
    top.appendChild(identity);
    var status = make('span', 'fp-status', labels.paused);
    top.appendChild(status);

    var lesson = make('div', 'fp-lesson');
    var progress = make('span', 'fp-progress');
    var narrative = make('p', 'fp-narrative');
    narrative.setAttribute('aria-live', 'off');
    var counter = make('span', 'fp-counter');
    var control = make('span', 'fp-control');
    var button = make('button', 'fp-toggle', labels.play);
    button.type = 'button';
    button.setAttribute('aria-pressed', 'true');
    control.appendChild(button);
    lesson.appendChild(progress);
    lesson.appendChild(narrative);
    lesson.appendChild(counter);
    lesson.appendChild(control);

    fig.insertBefore(top, fig.firstChild);
    var cap = fig.querySelector('figcaption');
    if (cap) fig.insertBefore(lesson, cap);
    else fig.appendChild(lesson);

    var state = {
      figure: fig,
      caption: figureCaption(fig),
      steps: semanticSteps(fig),
      stepIndex: -1,
      top: top,
      status: status,
      progress: progress,
      narrative: narrative,
      counter: counter,
      button: button,
      timer: 0,
      replayTimer: 0,
      guardTimer: 0,
      liveTimer: 0,
      internalClicks: 0,
      userPaused: false,
      playing: false,
      highlighted: null
    };
    setNarrative(state, state.caption, false);
    counter.textContent = state.steps.length ? '0 / ' + state.steps.length : '';
    setPlaying(state, false);

    button.addEventListener('click', function (event) {
      event.stopPropagation();
      if (state.playing) stop(state, true);
      else {
        state.userPaused = false;
        start(state, true);
      }
    });
    fig.addEventListener('click', function (event) {
      if (state.internalClicks || event.target.closest('.fp-control')) return;
      if (event.target.closest('button, input, select, textarea, [data-note]')) {
        stop(state, true);
        var note = event.target.closest('[data-note]');
        setNarrative(state, note && note.getAttribute('data-note'), true);
      }
    }, true);
    return state;
  }

  function init() {
    Array.prototype.forEach.call(document.querySelectorAll('figure'), function (fig, index) {
      var state = mount(fig, index);
      if (state) figures.push(state);
    });
    if (!figures.length) return;
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.18) visible.set(entry.target, entry.intersectionRatio);
          else visible.delete(entry.target);
        });
        chooseActive();
      }, { threshold: [0, 0.18, 0.35, 0.6] });
      figures.forEach(function (state) { observer.observe(state.figure); });
    } else {
      visible.set(figures[0].figure, 1);
      chooseActive();
    }
    document.addEventListener('visibilitychange', chooseActive);
    window.addEventListener('pagehide', function () { if (active) stop(active, false); });
    window.__figurePlayback = {
      figures: figures,
      active: function () { return active; },
      play: function (index) { if (figures[index]) { visible.set(figures[index].figure, 1); start(figures[index], true); } },
      pause: function () { if (active) stop(active, true); }
    };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 40); });
  else setTimeout(init, 40);
})();
