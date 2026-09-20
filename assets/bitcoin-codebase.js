(() => {
  const explorer = document.querySelector('[data-code-explorer]');
  if (explorer) {
    const tabs = [...explorer.querySelectorAll('[role="tab"]')];
    const panels = [...explorer.querySelectorAll('[role="tabpanel"]')];
    const select = tab => {
      tabs.forEach(item => {
        const active = item === tab;
        item.setAttribute('aria-selected', String(active));
        item.tabIndex = active ? 0 : -1;
      });
      panels.forEach(panel => { panel.hidden = panel.id !== tab.getAttribute('aria-controls'); });
    };
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => select(tab));
      tab.addEventListener('keydown', event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        let next = index;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        select(tabs[next]);
        tabs[next].focus();
      });
    });
  }

  const flow = document.querySelector('[data-flow]');
  if (!flow) return;
  const steps = [
    { title: '1. RPC receives signed bytes', file: 'src/rpc/mempool.cpp', explain: 'Decode hex, apply caller limits, then call BroadcastTransaction.', copy: 'The RPC layer parses the submitted hex and enforces caller-facing limits. It does not decide whether the transaction can enter the chain.' },
    { title: '2. Node checks local acceptance', file: 'src/node/transaction.cpp', explain: 'Test fees and mempool admission before marking the tx for announcement.', copy: 'BroadcastTransaction checks confirmed and mempool state, then asks ChainstateManager to process the transaction. The normal RPC path admits locally before relay.' },
    { title: '3. Mempool applies consensus and policy', file: 'src/validation.cpp', explain: 'Validate inputs and scripts, then apply fee and resource policy.', copy: 'AcceptToMemoryPool evaluates the spend against the active UTXO view and this node’s mempool rules. Valid here means acceptable to this node right now.' },
    { title: '4. Peers announce and request data', file: 'src/net_processing.cpp', explain: 'Track peer knowledge and move transaction data through P2P messages.', copy: 'The peer manager handles announcements, transaction messages, missing parents and packages. Receiving peers independently run their own acceptance path.' },
    { title: '5. A miner builds a candidate block', file: 'src/node/miner.cpp', explain: 'Select mempool chunks, construct the coinbase and test the template.', copy: 'BlockAssembler starts at the current tip and chooses transactions under block limits. Mining work is performed against the resulting candidate header.' },
    { title: '6. A full node connects valid state', file: 'src/validation.cpp + src/coins.cpp', explain: 'Validate the block, activate the best chain and update the UTXO view.', copy: 'When a valid block becomes active, its inputs are spent and new outputs are added. This state transition is confirmation from this node’s current view.' }
  ];
  const nodes = [...flow.querySelectorAll('[data-node]')];
  const progress = flow.querySelector('.flow-progress');
  const packet = flow.querySelector('.flow-packet');
  const title = flow.querySelector('#flow-title');
  const file = flow.querySelector('#flow-file');
  const explain = flow.querySelector('#flow-explain');
  const copy = flow.querySelector('#flow-copy');
  const count = flow.querySelector('#flow-count');
  const status = flow.querySelector('#flow-status');
  const pause = flow.querySelector('[data-flow-action="pause"]');
  const next = flow.querySelector('[data-flow-action="next"]');
  const replay = flow.querySelector('[data-flow-action="replay"]');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let step = 0;
  let playing = true;
  let visible = false;
  let timer;
  const render = () => {
    flow.dataset.step = String(step);
    flow.dataset.playing = String(playing);
    nodes.forEach((node, index) => {
      node.classList.toggle('is-past', index < step);
      node.classList.toggle('is-current', index === step);
    });
    progress.style.strokeDashoffset = String(100 - (step / (steps.length - 1)) * 100);
    packet.style.transform = `translate(${92 + step * 107.2}px,69px)`;
    title.textContent = steps[step].title;
    file.textContent = steps[step].file;
    explain.textContent = steps[step].explain;
    copy.textContent = steps[step].copy;
    count.textContent = `${step + 1} / ${steps.length}`;
    status.textContent = reduced ? playing ? 'Playing automatically. Motion reduced.' : 'Paused. Motion reduced.' : playing ? 'Playing automatically' : 'Paused';
    pause.textContent = playing ? 'Pause' : 'Play';
  };
  const schedule = () => {
    clearTimeout(timer);
    if (!playing || !visible) return;
    timer = setTimeout(() => {
      step = (step + 1) % steps.length;
      render();
      schedule();
    }, 6000);
  };
  pause.addEventListener('click', () => {
    playing = !playing;
    render();
    schedule();
  });
  next.addEventListener('click', () => {
    step = (step + 1) % steps.length;
    render();
    schedule();
  });
  replay.addEventListener('click', () => {
    step = 0;
    playing = true;
    render();
    schedule();
  });
  const observer = new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    if (!visible) clearTimeout(timer);
    else schedule();
  }, { threshold: 0.25 });
  observer.observe(flow);
  render();
})();
