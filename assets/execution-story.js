(() => {
  const coin = document.documentElement.dataset.coin;
  if (!['solana', 'sui'].includes(coin) || document.querySelector('.exec-story')) return;

  const profiles = {
    solana: {
      name: 'Solana',
      logo: 'assets/coins/solana.svg',
      eyebrow: 'A live execution story',
      title: 'Why some transactions fly together and others wait',
      intro: 'Watch three transactions declare the accounts they will change. The scheduler can run safe work together because it can see every overlap before execution.',
      switchLabel: 'Make two touch Noor wallet',
      independentLabel: 'All accounts are independent',
      conflictLabel: 'Noor wallet is shared',
      gateIdle: 'Account locks',
      gateConflict: 'Write lock found',
      defaultTransactions: [
        { id: 'tx1', person: 'Mira', action: 'Mira pays Noor', detail: 'Send 2 SOL', resources: ['Mira wallet', 'Noor wallet'] },
        { id: 'tx2', person: 'Omar', action: 'Omar mints a ticket', detail: 'Mint Ticket 84', resources: ['Omar wallet', 'Ticket mint'] },
        { id: 'tx3', person: 'Lina', action: 'Lina swaps SOL', detail: 'Use Pool 17', resources: ['Lina wallet', 'Pool 17'] }
      ],
      conflictTransactions: [
        { id: 'tx1', person: 'Mira', action: 'Mira pays Noor', detail: 'Send 2 SOL', resources: ['Mira wallet', 'Noor wallet'] },
        { id: 'tx2', person: 'Omar', action: 'Omar mints a ticket', detail: 'Mint Ticket 84', resources: ['Omar wallet', 'Ticket mint'] },
        { id: 'tx3', person: 'Lina', action: 'Lina pays Noor', detail: 'Send 1 SOL', resources: ['Lina wallet', 'Noor wallet'] }
      ],
      stages: {
        clear: [
          ['01', 'Three instructions arrive', 'Mira, Omar, and Lina submit different work. Nothing has executed yet.'],
          ['02', 'The runtime reads every account list', 'Each transaction names the accounts it can change. No pair overlaps, so no write lock collides.'],
          ['03', 'Sealevel opens three lanes', 'The three resource sets are independent. All three can execute in the same wave.'],
          ['04', 'One wave applies all three', 'Parallel execution changed the schedule, not the result. Every account received one valid update.']
        ],
        conflict: [
          ['01', 'Three instructions arrive', 'Mira and Lina now both want to change Noor wallet. Nothing has executed yet.'],
          ['02', 'The runtime finds one collision', 'Mira and Lina both declare Noor wallet as writable. Their order now matters.'],
          ['03', 'One write waits behind the other', 'Mira executes first. Lina queues on the same account lock while Omar still runs beside them.'],
          ['04', 'Two waves preserve one safe order', 'Mira and Omar apply first. Lina follows after Noor wallet is released. No updates race.']
        ]
      }
    },
    sui: {
      name: 'Sui',
      logo: 'assets/coins/sui.svg',
      eyebrow: 'A live execution story',
      title: 'When Sui objects move together',
      intro: 'Watch three transactions name the objects they will change. Work without dependencies may execute concurrently. Shared object work still needs an agreed order through current Sui consensus.',
      switchLabel: 'Make two touch Bazaar',
      independentLabel: 'All objects are independently owned',
      conflictLabel: 'Bazaar is a shared object',
      gateIdle: 'Object check',
      gateConflict: 'Consensus order',
      defaultTransactions: [
        { id: 'tx1', person: 'Mira', action: 'Mira sends Moonstone', detail: 'Owned object 104', resources: ['Moonstone 104'] },
        { id: 'tx2', person: 'Noor', action: 'Noor upgrades Sword', detail: 'Owned object 205', resources: ['Sword 205'] },
        { id: 'tx3', person: 'Omar', action: 'Omar lists Crown', detail: 'Owned object 306', resources: ['Crown 306'] }
      ],
      conflictTransactions: [
        { id: 'tx1', person: 'Mira', action: 'Mira buys in Bazaar', detail: 'Shared object call', resources: ['Mira coin', 'Bazaar shared'] },
        { id: 'tx2', person: 'Noor', action: 'Noor upgrades Sword', detail: 'Owned object 205', resources: ['Sword 205'] },
        { id: 'tx3', person: 'Omar', action: 'Omar bids in Bazaar', detail: 'Shared object call', resources: ['Omar coin', 'Bazaar shared'] }
      ],
      stages: {
        clear: [
          ['01', 'Three object actions arrive', 'Moonstone, Sword, and Crown have different owners and different current versions.'],
          ['02', 'The runtime inspects object dependencies', 'Each transaction changes a different owned object. The execution scheduler finds no shared input between them.'],
          ['03', 'Three execution paths open together', 'Work without dependencies may execute concurrently once the protocol has ordered it. This model does not bypass consensus.'],
          ['04', 'One wave applies three updates', 'Each owned object advances once. This is an execution schedule, not a finality or throughput claim.']
        ],
        conflict: [
          ['01', 'Two calls target one shared object', 'Mira and Omar both submit an action against Bazaar. Noor still touches only an owned Sword.'],
          ['02', 'Validators find the shared dependency', 'The Bazaar calls can affect each other, so current Sui consensus must place them in one agreed order before execution.'],
          ['03', 'Consensus orders the Bazaar calls', 'Mira goes first and Omar waits behind that decision. Noor\'s owned object remains independent.'],
          ['04', 'The agreed order applies safe versions', 'Bazaar advances in sequence while Sword remains dependency free. This model does not bypass Sui consensus.']
        ]
      }
    }
  };

  const profile = profiles[coin];
  const lead = document.querySelector('.lead');
  if (!lead) return;

  const story = document.createElement('section');
  story.className = `exec-story exec-story-${coin}`;
  story.setAttribute('aria-labelledby', 'exec-story-title');
  story.innerHTML = `
    <div class="est-head">
      <div class="est-brandmark"><img src="${profile.logo}" alt="${profile.name} logo" width="48" height="48"></div>
      <div><p class="est-eyebrow">${profile.eyebrow}</p><h2 id="exec-story-title">${profile.title}</h2></div>
    </div>
    <p class="est-intro">${profile.intro}</p>
    <div class="est-narrator" aria-live="off" aria-atomic="true">
      <span class="est-stage-number">01</span>
      <div><strong class="est-stage-title"></strong><p class="est-stage-copy"></p></div>
      <div class="est-stage-dots" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
    </div>
    <div class="est-scene" role="img" aria-label="Animated transaction execution schedule">
      <div class="est-zone est-zone-in"><span>Arrive</span></div>
      <div class="est-zone est-zone-read"><span>Inspect resources</span></div>
      <div class="est-zone est-zone-run"><span class="est-run-label">Execute</span></div>
      <div class="est-zone est-zone-done"><span>Apply updates</span></div>
      <div class="est-gate"><img src="${profile.logo}" alt="" width="24" height="24"><span>${profile.gateIdle}</span></div>
      <div class="est-lane est-lane-one"><span>Lane 1</span></div>
      <div class="est-lane est-lane-two"><span>Lane 2</span></div>
      <div class="est-lane est-lane-three"><span>Lane 3</span></div>
      <div class="est-collision" aria-hidden="true"><span></span><b>same writable resource</b></div>
      <div class="est-transactions"></div>
    </div>
    <div class="est-result" aria-live="polite"><span class="est-result-mark"></span><strong></strong><small></small></div>
    <div class="est-controls">
      <button type="button" class="est-conflict" aria-pressed="false"><span class="est-switch" aria-hidden="true"><i></i></span><span>${profile.switchLabel}</span></button>
      <div class="est-playback">
        <button type="button" class="est-pause">Pause</button>
        <button type="button" class="est-step">Next stage</button>
        <button type="button" class="est-replay">Replay</button>
      </div>
    </div>
  `;
  lead.insertAdjacentElement('afterend', story);

  const transactionRoot = story.querySelector('.est-transactions');
  const narratorNumber = story.querySelector('.est-stage-number');
  const narratorTitle = story.querySelector('.est-stage-title');
  const narratorCopy = story.querySelector('.est-stage-copy');
  const dots = [...story.querySelectorAll('.est-stage-dots i')];
  const conflictButton = story.querySelector('.est-conflict');
  const pauseButton = story.querySelector('.est-pause');
  const stepButton = story.querySelector('.est-step');
  const replayButton = story.querySelector('.est-replay');
  const result = story.querySelector('.est-result');
  const resultTitle = result.querySelector('strong');
  const resultCopy = result.querySelector('small');
  const narrator = story.querySelector('.est-narrator');
  const gateLabel = story.querySelector('.est-gate span');
  const runLabel = story.querySelector('.est-run-label');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let conflict = false;
  let stage = 0;
  let paused = false;
  let visible = false;
  let timer;

  const intersects = (left, right) => left.some(item => right.includes(item));

  function buildSchedule(transactions) {
    const scheduled = [];
    transactions.forEach((transaction, index) => {
      let wave = 0;
      let lane = index;
      scheduled.forEach(previous => {
        if (intersects(transaction.resources, previous.resources)) {
          wave = Math.max(wave, previous.wave + 1);
          lane = previous.lane;
        }
      });
      scheduled.push({ ...transaction, wave, lane });
    });
    return scheduled;
  }

  function currentTransactions() {
    return conflict ? profile.conflictTransactions : profile.defaultTransactions;
  }

  function renderTransactions() {
    const schedule = buildSchedule(currentTransactions());
    const repeated = schedule.flatMap((transaction, index) => schedule.slice(0, index).flatMap(previous => transaction.resources.filter(resource => previous.resources.includes(resource))));
    transactionRoot.innerHTML = schedule.map((transaction, index) => {
      const resourceTags = transaction.resources.map(resource => `<span class="${repeated.includes(resource) ? 'is-shared' : ''}">${resource}</span>`).join('');
      return `<article class="est-tx" data-index="${index}" data-wave="${transaction.wave}" data-lane="${transaction.lane}">
        <div class="est-tx-top"><img src="${profile.logo}" alt="" width="18" height="18"><b>TX ${index + 1}</b><em>${transaction.detail}</em></div>
        <strong>${transaction.action}</strong>
        <div class="est-resources">${resourceTags}</div>
        <span class="est-state">waiting</span>
      </article>`;
    }).join('');
    story.dataset.conflict = conflict ? 'true' : 'false';
    gateLabel.textContent = conflict ? profile.gateConflict : profile.gateIdle;
    runLabel.textContent = coin === 'sui' && conflict ? 'Order, then execute' : 'Execute';
    return schedule;
  }

  function setCardPositions(schedule) {
    const cards = [...story.querySelectorAll('.est-tx')];
    cards.forEach((card, index) => {
      const transaction = schedule[index];
      const rows = [18, 50, 82];
      const mobileLane = rows[index];
      let x = 14;
      let y = rows[index];
      let mobileX = mobileLane;
      let mobileY = 14;
      let state = 'waiting';
      if (stage === 1) {
        x = 25;
        mobileY = 36;
        state = 'resources declared';
      }
      if (stage === 2) {
        x = transaction.wave === 0 ? 71 : 25;
        y = rows[transaction.lane] || y;
        mobileY = transaction.wave === 0 ? 64 : 72;
        state = transaction.wave === 0 ? 'executing' : 'queued';
      }
      if (stage === 3) {
        x = 86;
        mobileY = 86;
        state = 'applied';
      }
      card.style.setProperty('--dx', `${x}%`);
      card.style.setProperty('--dy', `${y}%`);
      card.style.setProperty('--mx', `${mobileX}%`);
      card.style.setProperty('--my', `${mobileY}%`);
      card.querySelector('.est-state').textContent = state;
      card.dataset.state = state;
    });
  }

  function renderStage() {
    const schedule = buildSchedule(currentTransactions());
    const words = profile.stages[conflict ? 'conflict' : 'clear'][stage];
    narratorNumber.textContent = words[0];
    narratorTitle.textContent = words[1];
    narratorCopy.textContent = words[2];
    dots.forEach((dot, index) => dot.classList.toggle('is-active', index <= stage));
    story.dataset.stage = String(stage);
    setCardPositions(schedule);
    if (stage === 3) {
      const waves = Math.max(...schedule.map(transaction => transaction.wave)) + 1;
      result.classList.add('is-visible');
      resultTitle.textContent = waves === 1 ? '1 execution wave' : `${waves} execution waves`;
      resultCopy.textContent = conflict ? `1 dependency found. ${profile.conflictLabel}.` : `0 dependencies found. ${profile.independentLabel}.`;
    } else {
      result.classList.remove('is-visible');
      resultTitle.textContent = 'Schedule in progress';
      resultCopy.textContent = 'The result appears after the final execution stage.';
    }
  }

  function clearTimer() {
    if (timer) window.clearTimeout(timer);
    timer = undefined;
  }

  function canPlay() {
    return visible && !document.hidden && !paused;
  }

  function queueNext() {
    clearTimer();
    if (!canPlay() || stage === 3) return;
    timer = window.setTimeout(() => {
      narrator.setAttribute('aria-live', 'off');
      stage += 1;
      renderStage();
      queueNext();
    }, 2600);
  }

  function restart(manual = false) {
    clearTimer();
    stage = 0;
    paused = false;
    pauseButton.textContent = 'Pause';
    narrator.setAttribute('aria-live', manual ? 'polite' : 'off');
    renderTransactions();
    renderStage();
    queueNext();
  }

  conflictButton.addEventListener('click', () => {
    conflict = !conflict;
    conflictButton.setAttribute('aria-pressed', String(conflict));
    restart(true);
  });

  pauseButton.addEventListener('click', () => {
    paused = !paused;
    pauseButton.textContent = paused ? 'Resume' : 'Pause';
    if (paused) clearTimer(); else queueNext();
  });

  stepButton.addEventListener('click', () => {
    paused = true;
    pauseButton.textContent = 'Resume';
    clearTimer();
    stage = stage === 3 ? 0 : stage + 1;
    narrator.setAttribute('aria-live', 'polite');
    renderStage();
  });

  replayButton.addEventListener('click', () => restart(true));

  const observer = new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    if (visible) queueNext(); else clearTimer();
  }, { threshold: 0.05 });
  observer.observe(story);

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) clearTimer(); else queueNext();
  });

  reducedMotion.addEventListener?.('change', () => {
    renderStage();
    queueNext();
  });

  renderTransactions();
  renderStage();
})();
