(() => {
  const mount = document.getElementById('route-lab');
  if (!mount || mount.querySelector('.acq-explorer')) return;

  const routes = {
    atomic: {
      tab: 'Atomic swap',
      title: 'Atomic swap one crypto asset for XMR',
      summary: 'No exchange holds both sides. The protocol links the two transfers and defines recovery paths if the swap stalls. Timing and recovery steps depend on the implementation.',
      nodes: [
        { lines: ['Your crypto', 'wallet'], icon: 'wallet' },
        { lines: ['Atomic swap', 'protocol'], icon: 'protocol' },
        { lines: ['Swap', 'counterparty'], icon: 'person' },
        { lines: ['Your Monero', 'wallet'], icon: 'monero' }
      ],
      boundary: 'Protocol completion and refund rules',
      trust: 'Trust needed: the swap software, the protocol rules, network confirmation, and a counterparty who completes. A refund path reduces loss risk but does not make the route risk free.',
      stages: [
        ['01', 'Start with an asset you already own', 'Your existing crypto stays in your wallet until you accept a swap with a counterparty.'],
        ['02', 'The protocol locks both transfer conditions', 'Cryptographic conditions and timeouts link the two legs. Neither side should receive one asset while keeping the other.'],
        ['03', 'The counterparty completes the linked swap', 'Both networks must confirm the required steps. Liquidity, software, timing, and counterparty completion still matter.'],
        ['04', 'XMR arrives or the refund path opens', 'A completed route sends XMR to your wallet. If completion fails, the protocol refund path depends on its timeout and correct execution.']
      ]
    },
    haveno: {
      tab: 'Haveno P2P',
      title: 'Trade directly through Haveno',
      summary: 'Two traders use a 2 of 3 multisig with an arbitrator. The external payment happens outside the Monero protocol, so its provider may know both identities.',
      nodes: [
        { lines: ['You', 'the buyer'], icon: 'person' },
        { lines: ['2 of 3', 'multisig'], icon: 'escrow' },
        { lines: ['Seller and', 'payment rail'], icon: 'payment' },
        { lines: ['Your Monero', 'wallet'], icon: 'monero' }
      ],
      boundary: 'Multisig escrow and external payment',
      trust: 'Trust needed: the trader, the Haveno software, the external payment rail, and the arbitrator if a dispute occurs. The payment provider may link real identities even though the XMR transfer uses Monero.',
      stages: [
        ['01', 'You choose an offer from another trader', 'Haveno coordinates the trade. It does not turn the external payment into a Monero transaction.'],
        ['02', 'Trade funds enter 2 of 3 multisig', 'The traders lock the trade XMR and security deposits with an arbitrator key available for disputes.'],
        ['03', 'Payment moves outside the protocol', 'The buyer uses the agreed bank or payment rail. That provider may know both identities and the transfer details.'],
        ['04', 'The traders release XMR to your wallet', 'Both trader signatures complete the normal release. If the traders disagree, the arbitrator can help resolve the escrow.']
      ]
    },
    exchange: {
      tab: 'Exchange',
      title: 'Buy through a custodial exchange',
      summary: 'The platform verifies identity, accepts payment, and credits an internal balance. You hold a claim on the platform until XMR reaches your own wallet.',
      nodes: [
        { lines: ['You and', 'identity check'], icon: 'identity' },
        { lines: ['Custodial', 'exchange'], icon: 'exchange' },
        { lines: ['Platform', 'balance'], icon: 'balance' },
        { lines: ['Your Monero', 'wallet'], icon: 'monero' }
      ],
      boundary: 'Exchange custody until withdrawal',
      trust: 'Trust needed: the exchange controls payment, identity records, the internal balance, and withdrawal access until XMR reaches your wallet.',
      stages: [
        ['01', 'The exchange verifies your identity', 'Your account and payment method are linked to the platform records before a purchase is allowed.'],
        ['02', 'Payment enters the exchange', 'The platform receives the payment and controls the trade execution inside its own systems.'],
        ['03', 'An internal balance shows XMR', 'This balance is a claim on the exchange. The platform still controls the coins and withdrawal access.'],
        ['04', 'Withdrawal moves XMR into self custody', 'Only a completed withdrawal to your own wallet ends exchange custody. Network confirmation completes the handoff.']
      ]
    }
  };

  const icon = type => {
    if (type === 'wallet') return '<path d="M-15-10h27a6 6 0 0 1 6 6v19h-33a5 5 0 0 1-5-5V-9a6 6 0 0 1 6-6h25"/><path d="M8 0h14v10H8a5 5 0 0 1 0-10Z"/><circle cx="10" cy="5" r="1.5" class="acq-fill"/>';
    if (type === 'protocol') return '<circle cx="-12" cy="0" r="8"/><circle cx="12" cy="0" r="8"/><path d="M-4-4h8M-4 4h8"/>';
    if (type === 'person') return '<circle cy="-8" r="7"/><path d="M-15 16c1-12 7-17 15-17s14 5 15 17"/>';
    if (type === 'escrow') return '<path d="M0-18 17-11v12c0 10-7 17-17 21C-10 18-17 11-17 1v-12Z"/><path d="M-7 1h14M0-6v14"/>';
    if (type === 'payment') return '<rect x="-21" y="-14" width="42" height="28" rx="3"/><path d="M-21-4h42M-13 7h9"/>';
    if (type === 'identity') return '<rect x="-21" y="-15" width="42" height="30" rx="3"/><circle cx="-10" cy="-3" r="5"/><path d="M-17 10c1-6 4-9 8-9s7 3 8 9M5-6h10M5 1h10M5 8h7"/>';
    if (type === 'exchange') return '<path d="M-21-9 0-20 21-9ZM-17-5v20M-6-5v20M6-5v20M17-5v20M-22 19h44"/>';
    if (type === 'balance') return '<rect x="-20" y="-16" width="40" height="10" rx="2"/><rect x="-16" y="-2" width="32" height="10" rx="2"/><rect x="-11" y="12" width="22" height="10" rx="2"/>';
    return '';
  };

  const explorer = document.createElement('div');
  explorer.className = 'acq-explorer';
  explorer.innerHTML = `
    <div class="acq-head">
      <span class="acq-logo"><img src="assets/coins/monero.svg" alt="Monero logo" width="44" height="44"></span>
      <div><p class="acq-kicker">Follow custody and trust</p><strong>Three ways XMR can reach your wallet</strong></div>
    </div>
    <div class="acq-routes" role="tablist" aria-label="Choose an acquisition route">
      ${Object.entries(routes).map(([key, route], index) => `<button type="button" role="tab" data-route="${key}" aria-selected="${index === 0}">${route.tab}</button>`).join('')}
    </div>
    <div class="acq-route-copy"><strong></strong><p></p></div>
    <div class="acq-narrator" aria-live="off" aria-atomic="true">
      <span class="acq-stage-number">01</span><div><strong></strong><p></p></div>
      <span class="acq-progress" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
    </div>
    <figure class="acq-figure">
      <svg class="acq-map" viewBox="0 35 680 200" role="img" aria-labelledby="acq-map-title acq-map-desc">
        <title id="acq-map-title">How XMR reaches your wallet</title>
        <desc id="acq-map-desc">A four stage route showing custody and trust boundaries.</desc>
        <defs><marker id="acq-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M1 1 9 5 1 9" fill="none" stroke="context-stroke" stroke-width="1.5"/></marker></defs>
        <rect class="acq-boundary" rx="12"/><text class="acq-boundary-label" text-anchor="middle"></text>
        <g class="acq-links"></g>
        <g class="acq-nodes"></g>
        <g class="acq-marker"><circle r="15"/><text text-anchor="middle" dominant-baseline="central">1</text></g>
      </svg>
      <figcaption><span class="figno">Route map</span> The numbered marker follows this explanation. Funds follow the protocol described at each stage. The outlined area marks the route's main trust boundary.</figcaption>
    </figure>
    <div class="acq-trust"><strong>Trust boundary</strong><p></p></div>
    <div class="acq-controls">
      <button type="button" class="acq-pause">Pause</button>
      <button type="button" class="acq-next">Next stage</button>
      <button type="button" class="acq-replay">Replay</button>
    </div>
  `;
  mount.append(explorer);

  const svg = explorer.querySelector('.acq-map');
  const nodesRoot = explorer.querySelector('.acq-nodes');
  const linksRoot = explorer.querySelector('.acq-links');
  const marker = explorer.querySelector('.acq-marker');
  const boundary = explorer.querySelector('.acq-boundary');
  const boundaryLabel = explorer.querySelector('.acq-boundary-label');
  const routeTitle = explorer.querySelector('.acq-route-copy strong');
  const routeSummary = explorer.querySelector('.acq-route-copy p');
  const narrator = explorer.querySelector('.acq-narrator');
  const stageNumber = explorer.querySelector('.acq-stage-number');
  const stageTitle = explorer.querySelector('.acq-narrator div strong');
  const stageCopy = explorer.querySelector('.acq-narrator div p');
  const progress = [...explorer.querySelectorAll('.acq-progress i')];
  const trustCopy = explorer.querySelector('.acq-trust p');
  const pauseButton = explorer.querySelector('.acq-pause');
  const nextButton = explorer.querySelector('.acq-next');
  const replayButton = explorer.querySelector('.acq-replay');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const mobileLayout = window.matchMedia('(max-width: 600px)');
  let routeKey = 'atomic';
  let stage = 0;
  let paused = false;
  let visible = false;
  let timer;
  let positions = [];

  function layout() {
    const mobile = mobileLayout.matches;
    svg.setAttribute('viewBox', mobile ? '0 0 340 540' : '0 35 680 200');
    positions = mobile
      ? [{ x: 170, y: 62 }, { x: 170, y: 190 }, { x: 170, y: 318 }, { x: 170, y: 446 }]
      : [{ x: 72, y: 145 }, { x: 250, y: 145 }, { x: 428, y: 145 }, { x: 606, y: 145 }];
    renderRoute(false);
  }

  function nodeMarkup(node, index) {
    const position = positions[index];
    const visual = node.icon === 'monero'
      ? '<circle class="acq-logo-disc" cy="-10" r="24"/><image href="assets/coins/monero.svg" x="-28" y="-38" width="56" height="56"/>'
      : `<g class="acq-icon" transform="translate(0 -11)">${icon(node.icon)}</g>`;
    return `<g class="acq-node" data-index="${index}" transform="translate(${position.x} ${position.y})">
      <rect x="-62" y="-51" width="124" height="102" rx="10"/>
      ${visual}
      <text text-anchor="middle"><tspan x="0" y="24">${node.lines[0]}</tspan><tspan x="0" y="40">${node.lines[1]}</tspan></text>
    </g>`;
  }

  function linkMarkup(index) {
    const from = positions[index];
    const to = positions[index + 1];
    if (mobileLayout.matches) return `<path data-link="${index}" d="M${from.x} ${from.y + 55}V${to.y - 57}"/>`;
    return `<path data-link="${index}" d="M${from.x + 66} ${from.y}H${to.x - 68}"/>`;
  }

  function updateBoundary(route) {
    if (mobileLayout.matches) {
      boundary.setAttribute('x', '92');
      boundary.setAttribute('y', '138');
      boundary.setAttribute('width', '156');
      boundary.setAttribute('height', '238');
      boundaryLabel.setAttribute('x', '170');
      boundaryLabel.setAttribute('y', '130');
    } else {
      boundary.setAttribute('x', '174');
      boundary.setAttribute('y', '72');
      boundary.setAttribute('width', '330');
      boundary.setAttribute('height', '146');
      boundaryLabel.setAttribute('x', '339');
      boundaryLabel.setAttribute('y', '48');
    }
    boundaryLabel.textContent = route.boundary;
  }

  function renderRoute(reset = true) {
    const route = routes[routeKey];
    routeTitle.textContent = route.title;
    routeSummary.textContent = route.summary;
    trustCopy.textContent = route.trust;
    nodesRoot.innerHTML = route.nodes.map(nodeMarkup).join('');
    linksRoot.innerHTML = [0, 1, 2].map(linkMarkup).join('');
    updateBoundary(route);
    svg.setAttribute('aria-label', `${route.tab}. ${route.summary}`);
    if (reset) stage = 0;
    renderStage();
  }

  function renderStage() {
    const route = routes[routeKey];
    const words = route.stages[stage];
    stageNumber.textContent = words[0];
    stageTitle.textContent = words[1];
    stageCopy.textContent = words[2];
    progress.forEach((item, index) => item.classList.toggle('is-active', index <= stage));
    explorer.dataset.stage = String(stage);
    [...nodesRoot.querySelectorAll('.acq-node')].forEach((node, index) => {
      node.classList.toggle('is-reached', index <= stage);
      node.classList.toggle('is-current', index === stage);
    });
    [...linksRoot.querySelectorAll('path')].forEach((link, index) => link.classList.toggle('is-reached', index < stage));
    const markerX = mobileLayout.matches ? positions[stage].x + 82 : positions[stage].x;
    const markerY = mobileLayout.matches ? positions[stage].y : positions[stage].y - 75;
    marker.style.transform = `translate(${markerX}px, ${markerY}px)`;
    marker.querySelector('text').textContent = String(stage + 1);
  }

  function clearTimer() {
    if (timer) window.clearTimeout(timer);
    timer = undefined;
  }

  function queueNext() {
    clearTimer();
    if (!visible || document.hidden || paused || stage === 3) return;
    timer = window.setTimeout(() => {
      narrator.setAttribute('aria-live', 'off');
      stage += 1;
      renderStage();
      queueNext();
    }, 6000);
  }

  function restart(manual = false) {
    clearTimer();
    stage = 0;
    paused = false;
    pauseButton.textContent = 'Pause';
    narrator.setAttribute('aria-live', manual ? 'polite' : 'off');
    renderStage();
    queueNext();
  }

  explorer.querySelectorAll('[data-route]').forEach(button => {
    button.addEventListener('click', () => {
      routeKey = button.dataset.route;
      explorer.querySelectorAll('[data-route]').forEach(item => item.setAttribute('aria-selected', String(item === button)));
      narrator.setAttribute('aria-live', 'polite');
      renderRoute(true);
      paused = false;
      pauseButton.textContent = 'Pause';
      queueNext();
    });
  });

  pauseButton.addEventListener('click', () => {
    paused = !paused;
    pauseButton.textContent = paused ? 'Resume' : 'Pause';
    if (paused) clearTimer(); else queueNext();
  });

  nextButton.addEventListener('click', () => {
    clearTimer();
    paused = true;
    pauseButton.textContent = 'Resume';
    narrator.setAttribute('aria-live', 'polite');
    stage = stage === 3 ? 0 : stage + 1;
    renderStage();
  });

  replayButton.addEventListener('click', () => restart(true));

  const observer = new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    if (visible) queueNext(); else clearTimer();
  }, { threshold: 0.05 });
  observer.observe(explorer);

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) clearTimer(); else queueNext();
  });

  mobileLayout.addEventListener?.('change', layout);
  reducedMotion.addEventListener?.('change', renderStage);
  layout();
})();
