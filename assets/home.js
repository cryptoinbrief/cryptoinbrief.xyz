(() => {
  const root = document.documentElement;
  const themeButton = document.getElementById('theme-toggle');
  let savedTheme;
  try { savedTheme = localStorage.getItem('cib-theme'); } catch { root.dataset.storage = 'unavailable'; }
  if (savedTheme === 'dark' || savedTheme === 'light') root.dataset.theme = savedTheme;
  function setThemeLabel() {
    themeButton.setAttribute('aria-label', root.dataset.theme === 'dark' ? 'Use light theme' : 'Use dark theme');
  }
  setThemeLabel();
  themeButton.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('cib-theme', root.dataset.theme); } catch { root.dataset.storage = 'unavailable'; }
    setThemeLabel();
  });
  const demo = document.getElementById('payment-demo');
  const heading = document.getElementById('step-title');
  const explanation = document.getElementById('step-description');
  const caption = document.getElementById('network-caption');
  const stepButtons = [...document.querySelectorAll('[data-go-step]')];
  const networks = {
    bitcoin: { name: 'Bitcoin', ticker: 'BTC', color: '#cd7200', mechanism: 'A miner proposes a block', description: 'Miners try hashes until one meets the difficulty target. The winning block proposes an order for transactions.', finality: 'Nodes check the block. Inclusion gives the payment one confirmation. Later proof of work makes replacing that history less likely.' },
    ethereum: { name: 'Ethereum', ticker: 'ETH', color: '#627eea', mechanism: 'A validator proposes a block', description: 'A selected validator proposes a block. Other validators attest to the chain they see as valid. Invalid blocks are rejected.', finality: 'Nodes verify the block and validators attest. Inclusion comes first. Finality requires votes from a supermajority of stake on checkpoints.' },
    solana: { name: 'Solana', ticker: 'SOL', color: '#8752d7', mechanism: 'A leader orders transactions', description: 'A scheduled leader records transactions. Validators check the block and vote to agree on the chain.', finality: 'Validators replay transactions and vote. Stake weighted votes move a block from processed to confirmed and then finalized.' }
  };
  let network = 'bitcoin';
  let step = 0;
  let timer;
  let autoplay = true;
  let inView = true;
  let tampered = false;
  let signatureState = 'pending';
  let proofVersion = 0;
  let keys;
  const encoder = new TextEncoder();
  const tamperButton = document.getElementById('demo-tamper');
  const proofResult = document.getElementById('proof-result');
  const play = document.getElementById('demo-play');
  async function checkSignature() {
    const version = ++proofVersion;
    signatureState = 'pending';
    tamperButton.disabled = true;
    render();
    try {
      if (!crypto.subtle) throw new Error('A secure browser context is required');
      keys ||= crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign', 'verify']);
      const pair = await keys;
      const signed = encoder.encode(`${network}:Alex:Sam:1`);
      const received = encoder.encode(`${network}:Alex:Sam:${tampered ? 9 : 1}`);
      const signature = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, pair.privateKey, signed);
      const valid = await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, pair.publicKey, signature, received);
      if (version !== proofVersion) return;
      signatureState = valid ? 'valid' : 'invalid';
      tamperButton.disabled = false;
    } catch (error) {
      if (version !== proofVersion) return;
      signatureState = 'unavailable';
      tamperButton.title = 'Signature verification needs a browser with Web Crypto on HTTPS or localhost.';
    }
    render();
  }
  function stop() {
    clearTimeout(timer);
    timer = undefined;
    play.textContent = 'Play from start';
    play.setAttribute('aria-pressed', 'false');
    demo.dataset.playing = 'false';
  }
  function render() {
    heading.parentElement.setAttribute('aria-live', autoplay ? 'off' : 'polite');
    const selected = networks[network];
    const states = [
      ['A payment starts with an instruction', 'Alex chooses Sam and an amount. The wallet builds a transaction in that network’s format.'],
      ['The owner signs, then broadcasts', 'A digital signature authorizes the payment. Other computers can check that signature without learning the private key.'],
      [selected.mechanism, selected.description],
      ['Validation comes before finality', selected.finality]
    ];
    const rejected = tampered && step > 0;
    if (rejected) {
      states[1] = ['Someone changes the amount after signing', `Alex signed a payment of 1 ${selected.ticker}. The altered message asks for 9. The old signature still belongs to the original message.`];
      states[2] = ['The signature check fails', 'The browser is checking the altered message against the original signature. It fails. Changing even one field invalidates the authorization.'];
      states[3] = ['No valid signature. No payment.', 'The nodes reject the changed payment. Alex keeps the original balance and Sam receives nothing. Reaching a miner or validator cannot fix a bad signature.'];
    }
    demo.dataset.step = String(step);
    demo.dataset.proof = step > 0 ? signatureState : 'pending';
    demo.dataset.scenario = tampered ? 'tampered' : 'original';
    demo.style.setProperty('--coin', selected.color);
    heading.textContent = states[step][0];
    explanation.textContent = states[step][1];
    caption.textContent = `${selected.name} · ${tampered ? 'altered payment' : 'original payment'}`;
    document.getElementById('alex-balance').textContent = `${step === 3 && signatureState === 'valid' ? 9 : 10} ${selected.ticker}`;
    document.getElementById('sam-balance').textContent = `${step === 3 && signatureState === 'valid' ? 1 : 0} ${selected.ticker}`;
    document.getElementById('record-amount').textContent = `${rejected ? 9 : 1} ${selected.ticker}`;
    document.querySelectorAll('.scene-coin').forEach(logo => logo.setAttribute('href', `assets/coins/${network}.svg`));
    document.getElementById('block-label').textContent = ['Create payment', 'Signed payment', 'Proposed block', 'Accepted block'][step];
    document.getElementById('block-status').textContent = ['A transaction is an instruction, not a coin file.', 'The signature authorizes Alex’s payment.', 'Every node checks the proposed block.', 'Sam’s balance updates. Finality comes later.'][step];
    document.querySelectorAll('.peer-status').forEach(label => { label.textContent = ['Waiting', 'Received', 'Checking…', 'Valid ✓'][step]; });
    if (rejected && step >= 2) {
      document.getElementById('block-label').textContent = 'Payment rejected';
      document.getElementById('block-status').textContent = 'An altered message cannot reuse a signature.';
      document.querySelectorAll('.peer-status').forEach(label => { label.textContent = 'Rejected'; });
    }
    proofResult.textContent = { pending: 'Checking signature…', valid: 'Signature verified', invalid: 'Signature rejected', unavailable: 'Web Crypto unavailable' }[signatureState];
    if (signatureState !== 'pending' && signatureState !== 'unavailable' && step < 2) proofResult.textContent = step === 0 ? 'Payment prepared' : (tampered ? 'Signed message altered' : 'Original payment signed');
    proofResult.dataset.state = step >= 2 ? signatureState : 'pending';
    tamperButton.textContent = tampered ? 'Restore the signed amount' : 'Change the signed amount';
    document.getElementById('demo-next').textContent = step === 3 ? 'Start over' : 'Next step →';
    stepButtons.forEach((button, index) => {
      if (index === step) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
  }
  async function advance() {
    if (!autoplay || !inView || document.hidden) { stop(); return; }
    step = (step + 1) % 4;
    if (step === 0) { tampered = !tampered; await checkSignature(); }
    if (!autoplay || !inView || document.hidden) return;
    render();
    timer = setTimeout(advance, step === 3 ? 5200 : 4200);
  }
  function start() {
    stop();
    autoplay = true;
    step = 0;
    render();
    play.textContent = 'Pause';
    play.setAttribute('aria-pressed', 'true');
    demo.dataset.playing = 'true';
    timer = setTimeout(advance, 3200);
  }
  play.addEventListener('click', () => { if (timer) { autoplay = false; stop(); } else start(); });
  document.getElementById('demo-next').addEventListener('click', () => {
    stop();
    autoplay = false;
    step = (step + 1) % 4;
    render();
  });
  stepButtons.forEach(button => button.addEventListener('click', () => {
    stop();
    autoplay = false;
    step = Number(button.dataset.goStep);
    render();
  }));
  document.querySelectorAll('[data-network]').forEach(button => button.addEventListener('click', () => {
    network = button.dataset.network;
    document.querySelectorAll('[data-network]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    render();
    checkSignature();
  }));
  tamperButton.addEventListener('click', async () => {
    stop();
    autoplay = false;
    tampered = !tampered;
    step = tampered ? 2 : 1;
    await checkSignature();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop();
    else if (autoplay && inView) start();
  });
  new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting;
    if (!inView) stop();
    else if (autoplay && !timer) start();
  }, { threshold: 0.2 }).observe(demo);
  render();
  checkSignature();
  start();
  let filter = 'all';
  const search = document.getElementById('topic-search');
  const topics = [...document.querySelectorAll('.topic')];
  function filterTopics() {
    const term = search.value.trim().toLowerCase();
    let count = 0;
    topics.forEach(topic => {
      const show = (filter === 'all' || topic.dataset.category.split(' ').includes(filter)) && topic.textContent.toLowerCase().includes(term);
      topic.hidden = !show;
      if (show) count++;
    });
    document.getElementById('empty-topics').hidden = count > 0;
    document.getElementById('results-count').textContent = `${count} guides`;
  }
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
    filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    filterTopics();
  }));
  search.addEventListener('input', filterTopics);
  filterTopics();
})();
