(() => {
  const lab = document.getElementById('paper-payment-lab');
  if (!lab) return;

  const modes = ['observer', 'recipient'];
  const copy = {
    observer: [
      'The same instruction begins both payments: move one coin from Alice to Bob.',
      'Bitcoin exposes the input links, output condition, and amount. CryptoNote v2 exposes a one-time output, a ring of possible spenders, a key image, and the amount.',
      'Bitcoin rejects a repeated output reference. CryptoNote rejects a repeated key image without naming the real ring member.'
    ],
    recipient: [
      'Bob opens his wallet and asks which output belongs to him.',
      'A Bitcoin wallet recognizes an output condition it can satisfy. A CryptoNote wallet scans with its private view key and derives the matching one-time output.',
      'Bob can spend in either design. The CryptoNote paper keeps his published address and real ring member out of the public evidence, but it does not hide the amount.'
    ]
  };
  const tabs = [...lab.querySelectorAll('[data-view-button]')];
  const status = lab.querySelector('.autoplay-state b');
  const narrator = lab.querySelector('.paper-narrator p');
  const count = lab.querySelector('.phase-count');
  const play = lab.querySelector('.play-toggle');
  const replay = lab.querySelector('.replay');
  let mode = 'observer';
  let phase = 0;
  let paused = false;
  let visible = false;
  let timers = [];

  const clear = () => {
    timers.forEach(window.clearTimeout);
    timers = [];
  };

  const paint = () => {
    lab.dataset.view = mode;
    lab.dataset.phase = String(phase);
    lab.dataset.paused = String(paused);
    narrator.textContent = copy[mode][phase];
    count.textContent = `${phase + 1} / 3`;
    tabs.forEach(tab => tab.setAttribute('aria-selected', String(tab.dataset.viewButton === mode)));
    play.textContent = paused ? 'Resume' : 'Pause';
    status.textContent = paused ? 'Paused' : visible ? 'Playing automatically' : 'Paused off screen';
  };

  const schedule = () => {
    clear();
    if (paused || !visible) return;
    timers.push(window.setTimeout(() => {
      phase = 1;
      paint();
    }, 1800));
    timers.push(window.setTimeout(() => {
      phase = 2;
      paint();
    }, 3700));
    timers.push(window.setTimeout(() => {
      mode = modes[(modes.indexOf(mode) + 1) % modes.length];
      phase = 0;
      paint();
      schedule();
    }, 6000));
  };

  const restart = nextMode => {
    if (nextMode) mode = nextMode;
    phase = 0;
    paint();
    schedule();
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => restart(tab.dataset.viewButton));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      tabs[next].focus();
      restart(tabs[next].dataset.viewButton);
    });
  });
  play.addEventListener('click', () => {
    paused = !paused;
    paint();
    schedule();
  });
  replay.addEventListener('click', () => restart());

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.target !== lab) return;
        visible = entry.isIntersecting && entry.intersectionRatio >= 0.2;
        paint();
        if (visible) schedule();
        else clear();
      });
    }, { threshold: [0, 0.2, 0.5] });
    observer.observe(lab);
  } else {
    visible = true;
    paint();
    schedule();
  }

  paint();
})();
