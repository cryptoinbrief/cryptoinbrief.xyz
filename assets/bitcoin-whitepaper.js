(() => {
  const mount = document.getElementById('pow-story');
  if (!mount || mount.querySelector('.pow-story')) return;

  const chapters = [
    ['01', 'A signature authorizes one payment', 'Alice signs a transaction that spends an earlier output and assigns the value to Bob. A signature proves authority. It does not prove that Alice did not sign a conflicting payment.'],
    ['02', 'The same input appears in two histories', 'One branch pays Bob. The competing branch returns the same value to Alice. Both signatures can be valid, so every full node needs one ordered history.'],
    ['03', 'Miners spend work extending a valid branch', 'Blocks point backward by hash. Changing an older block changes its hash, so the attacker must redo that block and every block after it.'],
    ['04', 'Nodes follow the valid chain with more work', 'A full node validates the rules first, then selects the valid history with the greatest cumulative proof of work. Node count is not the deciding weight.']
  ];

  const story = document.createElement('div');
  story.className = 'pow-story';
  story.dataset.stage = '0';
  story.dataset.playing = 'true';
  story.innerHTML = `
    <div class="pow-head"><img src="assets/coins/bitcoin.svg" alt="Bitcoin logo" width="54" height="54"><div><p class="pow-kicker">One payment, two histories</p><h3>How proof of work settles the conflict</h3></div></div>
    <div class="pow-chapters" role="tablist" aria-label="Whitepaper model chapters">${chapters.map((chapter, index) => `<button type="button" role="tab" data-chapter="${index}" aria-selected="${index === 0}">${chapter[0]} ${['Sign','Conflict','Work','Select'][index]}</button>`).join('')}</div>
    <div class="pow-narrator" aria-live="off" aria-atomic="true"><span class="pow-number"></span><div><strong></strong><p></p></div></div>
    <div class="pow-scene" role="img" aria-label="A signed payment splits into two candidate block histories. The valid history with more cumulative work is selected.">
      <div class="pow-wallets">
        <div class="pow-wallet"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 8h22a3 3 0 0 1 3 3v15H7a4 4 0 0 1-4-4V9a5 5 0 0 1 5-5h16"/><path d="M20 14h10v7H20a3.5 3.5 0 0 1 0-7Z"/></svg><div><b>Alice's wallet</b><span>spends output #17</span></div></div>
        <div class="pow-payment">signed tx</div>
        <div class="pow-wallet"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 8h22a3 3 0 0 1 3 3v15H7a4 4 0 0 1-4-4V9a5 5 0 0 1 5-5h16"/><path d="M20 14h10v7H20a3.5 3.5 0 0 1 0-7Z"/></svg><div><b>Bob's wallet</b><span>expects the payment</span></div></div>
      </div>
      <div class="pow-stage">
        <div class="pow-chain-label"><strong>Public branch</strong><span class="pow-honest-work"></span></div><div class="pow-chain pow-public"></div>
        <div class="pow-chain-label"><strong>Competing branch</strong><span class="pow-attack-work"></span></div><div class="pow-chain pow-competing"></div>
        <p class="pow-chain-status"></p>
      </div>
    </div>
    <div class="pow-tuning">
      <div class="pow-field"><label for="pow-confirmations">Confirmations of Bob's payment</label><output id="pow-confirmations-value">3</output><input id="pow-confirmations" type="range" min="1" max="6" step="1" value="3"></div>
      <div class="pow-field"><label for="pow-attacker">Attacker share of total work</label><output id="pow-attacker-value">20%</output><input id="pow-attacker" type="range" min="10" max="45" step="5" value="20"></div>
      <p class="pow-risk"></p>
    </div>
    <div class="pow-controls"><button type="button" class="pow-pause">Pause</button><button type="button" class="pow-next">Next chapter</button><button type="button" class="pow-replay">Replay</button></div>
    <p class="pow-model">Teaching model: each drawn block has equal difficulty, so block count stands in for cumulative work. Real nodes compare chainwork and validate every consensus rule. The probability display evaluates the whitepaper's Poisson model, whose assumptions are explained below.</p>`;
  mount.replaceChildren(story);

  const number = story.querySelector('.pow-number');
  const title = story.querySelector('.pow-narrator strong');
  const copy = story.querySelector('.pow-narrator p');
  const publicChain = story.querySelector('.pow-public');
  const competingChain = story.querySelector('.pow-competing');
  const status = story.querySelector('.pow-chain-status');
  const confirmations = story.querySelector('#pow-confirmations');
  const attacker = story.querySelector('#pow-attacker');
  const confirmationValue = story.querySelector('#pow-confirmations-value');
  const attackerValue = story.querySelector('#pow-attacker-value');
  const risk = story.querySelector('.pow-risk');
  const pauseButton = story.querySelector('.pow-pause');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let stage = 0;
  let timer;
  let visible = false;
  let paused = false;

  function factorial(value) {
    let result = 1;
    for (let index = 2; index <= value; index += 1) result *= index;
    return result;
  }

  function successProbability(q, z) {
    if (q >= 0.5) return 1;
    const p = 1 - q;
    const lambda = z * q / p;
    let sum = 1;
    for (let k = 0; k <= z; k += 1) {
      const poisson = Math.exp(-lambda) * Math.pow(lambda, k) / factorial(k);
      sum -= poisson * (1 - Math.pow(q / p, z - k));
    }
    return Math.max(0, Math.min(1, sum));
  }

  function blockMarkup(index, kind) {
    const payment = kind === 'public' && index === 1;
    const conflict = kind === 'competing' && index === 1;
    const common = index === 0;
    return `<span class="pow-block${payment ? ' is-payment' : ''}${conflict ? ' is-conflict' : ''}${common ? ' is-common' : ''}" style="--i:${index}">${payment ? 'Bob paid' : conflict ? 'conflict' : common ? 'shared tip' : `B${index}`}</span>`;
  }

  function renderChains() {
    const z = Number(confirmations.value);
    const q = Number(attacker.value) / 100;
    const publicWork = z;
    const competingWork = Math.max(1, Math.round(z * q / (1 - q)));
    const publicBlocks = publicWork + 1;
    const competingBlocks = competingWork + 1;
    publicChain.innerHTML = Array.from({length: publicBlocks}, (_, index) => blockMarkup(index, 'public')).join('');
    competingChain.innerHTML = Array.from({length: competingBlocks}, (_, index) => blockMarkup(index, 'competing')).join('');
    const publicWins = publicWork > competingWork;
    publicChain.classList.toggle('is-selected', stage === 3 && publicWins);
    competingChain.classList.toggle('is-selected', stage === 3 && !publicWins);
    publicChain.classList.toggle('is-stale', stage === 3 && !publicWins);
    competingChain.classList.toggle('is-stale', stage === 3 && publicWins);
    story.querySelector('.pow-honest-work').textContent = `${publicWork} equal-work block${publicWork === 1 ? '' : 's'} after the fork`;
    story.querySelector('.pow-attack-work').textContent = `${competingWork} equal-work block${competingWork === 1 ? '' : 's'} after the fork in this expected-progress view`;
    status.innerHTML = stage < 3 ? 'Both branches can contain correctly signed transactions. Nodes still validate every block.' : `<strong>${publicWins ? 'The branch containing Bob\'s payment is selected.' : 'The competing branch overtakes in this model.'}</strong> Selection happens after rule validation and by cumulative work.`;
    const probability = successProbability(q, z);
    const formatted = probability < 0.001 ? `${(probability * 100).toFixed(3)}%` : `${(probability * 100).toFixed(2)}%`;
    risk.innerHTML = `Under the paper's attacker model, a miner with <strong>${Math.round(q * 100)}%</strong> of total work has about a <strong>${formatted}</strong> chance of eventually catching up from <strong>${z}</strong> confirmation${z === 1 ? '' : 's'}. This is a model, not a promise.`;
    confirmationValue.value = String(z);
    attackerValue.value = `${Math.round(q * 100)}%`;
  }

  function render() {
    const chapter = chapters[stage];
    story.dataset.stage = String(stage);
    number.textContent = chapter[0];
    title.textContent = chapter[1];
    copy.textContent = chapter[2];
    story.querySelectorAll('[data-chapter]').forEach((button, index) => button.setAttribute('aria-selected', String(index === stage)));
    renderChains();
  }

  function clearTimer() {
    if (timer) window.clearTimeout(timer);
    timer = undefined;
  }

  function queue() {
    clearTimer();
    if (!visible || document.hidden || paused || stage === chapters.length - 1) return;
    timer = window.setTimeout(() => {
      stage += 1;
      render();
      queue();
    }, 6000);
  }

  function selectStage(next, manual) {
    stage = (next + chapters.length) % chapters.length;
    if (manual) {
      paused = true;
      pauseButton.textContent = 'Resume';
      story.dataset.playing = 'false';
      story.querySelector('.pow-narrator').setAttribute('aria-live', 'polite');
    }
    render();
    queue();
  }

  story.querySelectorAll('[data-chapter]').forEach(button => button.addEventListener('click', () => selectStage(Number(button.dataset.chapter), true)));
  story.querySelector('.pow-next').addEventListener('click', () => selectStage(stage + 1, true));
  story.querySelector('.pow-replay').addEventListener('click', () => {
    paused = false;
    pauseButton.textContent = 'Pause';
    story.dataset.playing = 'true';
    story.querySelector('.pow-narrator').setAttribute('aria-live', 'polite');
    selectStage(0, false);
  });
  pauseButton.addEventListener('click', () => {
    paused = !paused;
    pauseButton.textContent = paused ? 'Resume' : 'Pause';
    story.dataset.playing = String(!paused);
    if (paused) clearTimer(); else queue();
  });
  [confirmations, attacker].forEach(input => input.addEventListener('input', () => {
    paused = true;
    pauseButton.textContent = 'Resume';
    story.dataset.playing = 'false';
    renderChains();
    clearTimer();
  }));

  const observer = new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    if (visible) queue(); else clearTimer();
  }, {threshold: 0.3});
  observer.observe(story);
  document.addEventListener('visibilitychange', () => document.hidden ? clearTimer() : queue());
  reducedMotion.addEventListener?.('change', render);
  render();
})();
