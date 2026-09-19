(() => {
  const page = location.pathname.split('/').pop();
  const kind = page === 'bitcoin-from-zero.html' ? 'bitcoin' : page === 'proof-of-stake.html' ? 'pos' : '';
  const lead = document.querySelector('.lead');
  if (!kind || !lead || document.querySelector('.cstory')) return;

  const wait = 3800;
  const encoder = new TextEncoder();
  const short = value => `${value.slice(0, 8)}…${value.slice(-5)}`;
  const sha256 = async value => {
    const bytes = await crypto.subtle.digest('SHA-256', encoder.encode(value));
    return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
  };

  const bitcoinLogo = '<img class="cstory-logo" src="assets/coins/bitcoin.svg" alt="Bitcoin">';
  const ethereumLogo = '<img class="cstory-logo" src="assets/coins/ethereum.svg" alt="Ethereum">';

  const controls = action => `
    <div class="cstory-controls">
      <button class="cstory-control cstory-pause" type="button" aria-pressed="false">Pause</button>
      <button class="cstory-control cstory-next" type="button">Next step</button>
      <button class="cstory-control cstory-replay" type="button">Replay</button>
      <span class="cstory-spacer"></span>
      ${action}
    </div>`;

  const bitcoinMarkup = `
    <section class="cstory cstory-bitcoin" data-kind="bitcoin" data-stage="0" aria-labelledby="cstory-title">
      <div class="cstory-topline">
        <div class="cstory-brand">${bitcoinLogo}<span>Bitcoin chain lab</span></div>
        <div class="cstory-step"><span class="cstory-stepnum">01</span><span class="cstory-stepof"> / 04</span></div>
      </div>
      <div class="cstory-heading">
        <div><span class="cstory-kicker">Change one rule. Watch what breaks.</span><h2 id="cstory-title">A block chain remembers every edit</h2></div>
        <div class="cstory-rule"><span>Rule under test</span><strong>Each block names the block before it</strong></div>
      </div>
      <div class="cstory-visual" aria-label="Three linked teaching blocks">
        <div class="cstory-chain" role="img" aria-label="Three blocks connected by previous hash pointers">
          <article class="cstory-block" data-block="0">
            <div class="cstory-blocktop"><span>BLOCK 840,001</span><span class="cstory-stateicon">✓</span></div>
            <div class="cstory-payment"><span class="cstory-token">₿</span><span><small>PAYMENT</small><strong class="cstory-pay0">Maya → Leo&nbsp; 0.80 BTC</strong></span></div>
            <dl><div><dt>PREV</dt><dd>GENESIS</dd></div><div><dt>HASH</dt><dd class="cstory-hash0">computing…</dd></div></dl>
            <span class="cstory-scan"></span>
          </article>
          <div class="cstory-link" data-link="0"><span class="cstory-packet">HASH</span><i></i><b>linked</b></div>
          <article class="cstory-block" data-block="1">
            <div class="cstory-blocktop"><span>BLOCK 840,002</span><span class="cstory-stateicon">✓</span></div>
            <div class="cstory-payment"><span class="cstory-token">₿</span><span><small>PAYMENT</small><strong>Leo → Noor&nbsp; 0.30 BTC</strong></span></div>
            <dl><div><dt>PREV</dt><dd class="cstory-prev1">computing…</dd></div><div><dt>HASH</dt><dd class="cstory-hash1">computing…</dd></div></dl>
            <span class="cstory-scan"></span>
          </article>
          <div class="cstory-link" data-link="1"><span class="cstory-packet">HASH</span><i></i><b>linked</b></div>
          <article class="cstory-block" data-block="2">
            <div class="cstory-blocktop"><span>BLOCK 840,003</span><span class="cstory-stateicon">✓</span></div>
            <div class="cstory-payment"><span class="cstory-token">₿</span><span><small>PAYMENT</small><strong>Noor → Sam&nbsp; 0.10 BTC</strong></span></div>
            <dl><div><dt>PREV</dt><dd class="cstory-prev2">computing…</dd></div><div><dt>HASH</dt><dd class="cstory-hash2">computing…</dd></div></dl>
            <span class="cstory-scan"></span>
          </article>
        </div>
        <div class="cstory-verdict"><span class="cstory-verdictmark">✓</span><div><small>NETWORK CHECK</small><strong class="cstory-verdict-title">All links agree</strong><p class="cstory-verdict-copy">The payment data and every previous hash pointer match.</p></div></div>
      </div>
      <div class="cstory-caption" aria-live="off"><span class="cstory-captionnum">01</span><div><strong class="cstory-captiontitle">Start with an honest chain</strong><p class="cstory-captioncopy">Each teaching block has payment data, its own SHA 256 digest, and the previous block’s digest.</p></div></div>
      ${controls('<button class="cstory-action cstory-tamper" type="button">Change earlier payment</button><button class="cstory-action cstory-rebuild" type="button">Rebuild links</button>')}
      <p class="cstory-disclosure">This teaching chain uses real SHA 256 digests. Real Bitcoin also requires valid transactions, consensus rules, and proof of work.</p>
    </section>`;

  const posMarkup = `
    <section class="cstory cstory-pos" data-kind="pos" data-stage="0" data-offline="false" aria-labelledby="cstory-title">
      <div class="cstory-topline">
        <div class="cstory-brand">${ethereumLogo}<span>Proof of stake lab</span></div>
        <div class="cstory-step"><span class="cstory-stepnum">01</span><span class="cstory-stepof"> / 04</span></div>
      </div>
      <div class="cstory-heading">
        <div><span class="cstory-kicker">Follow one block from proposal to finality</span><h2 id="cstory-title">A proposed block is not yet final</h2></div>
        <div class="cstory-rule"><span>Rule under test</span><strong>At least two thirds of stake must agree</strong></div>
      </div>
      <div class="cstory-visual cstory-posvisual">
        <div class="cstory-validatorrow" aria-label="Three illustrative validators">
          <article class="cstory-validator" data-validator="a"><div class="cstory-node"><span>A</span><i></i></div><strong>Atlas</strong><small>50 stake</small><span class="cstory-vote">VOTE</span></article>
          <article class="cstory-validator" data-validator="b"><div class="cstory-node"><span>B</span><i></i></div><strong>Birch</strong><small>30 stake</small><span class="cstory-vote">VOTE</span></article>
          <article class="cstory-validator" data-validator="c"><div class="cstory-node"><span>C</span><i></i></div><strong>Cedar</strong><small>20 stake</small><span class="cstory-vote">VOTE</span></article>
        </div>
        <div class="cstory-posflow">
          <div class="cstory-slot"><small>SLOT 12,408</small><strong class="cstory-slot-title">Choosing proposer</strong><div class="cstory-lottery"><i style="--stake:50%"></i><i style="--stake:30%"></i><i style="--stake:20%"></i><span></span></div></div>
          <div class="cstory-proposed"><span class="cstory-minieth">${ethereumLogo}</span><div><small>BLOCK</small><strong>#21,044,102</strong><span class="cstory-blockstatus">waiting</span></div></div>
          <div class="cstory-arrow"><i></i><span>stake votes</span></div>
          <div class="cstory-checkpointstack">
            <div class="cstory-checkpoint"><div class="cstory-gauge"><i></i><span class="cstory-gaugevalue">0%</span></div><div><small>CHECKPOINT C1</small><strong class="cstory-finality">Not justified</strong><span class="cstory-threshold">needs 66.7%</span></div></div>
            <div class="cstory-ffglink"><i></i><span class="cstory-linklabel">later link</span></div>
            <div class="cstory-nextcheckpoint"><small>CHECKPOINT C2</small><strong class="cstory-nextfinality">Waiting for C1</strong></div>
          </div>
        </div>
        <div class="cstory-outage"><span>40% OF NETWORK STAKE OFFLINE</span><i></i></div>
      </div>
      <div class="cstory-caption" aria-live="off"><span class="cstory-captionnum">01</span><div><strong class="cstory-captiontitle">First, choose a proposer</strong><p class="cstory-captioncopy">This simplified draw gives more selection weight to validators with more stake. It does not reproduce a live network.</p></div></div>
      ${controls('<button class="cstory-action cstory-offline" type="button">Take 40% offline</button><button class="cstory-action cstory-restore" type="button">Restore validators</button>')}
      <p class="cstory-disclosure">Simplified Casper FFG teaching model. Inclusion, justification, and finalization are separate. A direct later supermajority link finalizes its source checkpoint. This demo does not imply every error is slashed.</p>
    </section>`;

  lead.insertAdjacentHTML('afterend', kind === 'bitcoin' ? bitcoinMarkup : posMarkup);
  const root = document.querySelector('.cstory');
  const stepNumber = root.querySelector('.cstory-stepnum');
  const captionNumber = root.querySelector('.cstory-captionnum');
  const caption = root.querySelector('.cstory-caption');
  const captionTitle = root.querySelector('.cstory-captiontitle');
  const captionCopy = root.querySelector('.cstory-captioncopy');
  const pauseButton = root.querySelector('.cstory-pause');
  let stage = 0;
  let manuallyPaused = false;
  let visible = false;
  let offline = false;
  let timer;
  let started = false;

  const copy = kind === 'bitcoin' ? [
    ['Start with an honest chain', 'Each teaching block has payment data, its own SHA 256 digest, and the previous block’s digest.'],
    ['Change one earlier payment', 'Maya’s payment changes from 0.80 to 8.00 BTC. Its new digest is different, but the next block still points to the old one.'],
    ['The network rejects the tip', 'The mismatch is visible before the changed history can be accepted. A later block cannot hide the broken pointer behind it.'],
    ['Rebuilding links is not enough', 'The pointers can be recalculated, but real Bitcoin would also require redoing proof of work and catching the honest chain.']
  ] : [
    ['First, choose a proposer', 'This simplified draw gives more selection weight to validators with more stake. It does not reproduce a live network.'],
    ['The proposer includes a block', 'Atlas publishes a candidate block. Inclusion gives validators something to vote on; it does not justify or finalize a checkpoint.'],
    ['Eighty percent justifies checkpoint C1', 'Atlas and Birch form an 80% link from an earlier justified source checkpoint to C1. That justifies C1. It does not finalize C1 yet.'],
    ['A later link finalizes C1', 'Another 80% link justifies checkpoint C2. Because it directly follows C1, that later link finalizes its source checkpoint, C1.']
  ];

  const bitcoinData = {
    honest: [],
    tampered: '',
    rebuilt: []
  };

  const computeBitcoin = async () => {
    const h0 = await sha256('840001|Maya>Leo|0.80 BTC|GENESIS');
    const h1 = await sha256(`840002|Leo>Noor|0.30 BTC|${h0}`);
    const h2 = await sha256(`840003|Noor>Sam|0.10 BTC|${h1}`);
    bitcoinData.honest = [h0, h1, h2];
    bitcoinData.tampered = await sha256('840001|Maya>Leo|8.00 BTC|GENESIS');
    const rebuilt1 = await sha256(`840002|Leo>Noor|0.30 BTC|${bitcoinData.tampered}`);
    const rebuilt2 = await sha256(`840003|Noor>Sam|0.10 BTC|${rebuilt1}`);
    bitcoinData.rebuilt = [bitcoinData.tampered, rebuilt1, rebuilt2];
    paintBitcoin();
  };

  const setText = (selector, value) => {
    const target = root.querySelector(selector);
    if (target) target.textContent = value;
  };

  const paintBitcoin = () => {
    if (!bitcoinData.honest.length) return;
    const hashes = stage === 3 ? bitcoinData.rebuilt : bitcoinData.honest;
    setText('.cstory-pay0', stage > 0 ? 'Maya → Leo  8.00 BTC' : 'Maya → Leo  0.80 BTC');
    setText('.cstory-hash0', short(stage === 1 || stage === 2 ? bitcoinData.tampered : hashes[0]));
    setText('.cstory-hash1', short(hashes[1]));
    setText('.cstory-hash2', short(hashes[2]));
    setText('.cstory-prev1', short(stage === 3 ? bitcoinData.rebuilt[0] : bitcoinData.honest[0]));
    setText('.cstory-prev2', short(stage === 3 ? bitcoinData.rebuilt[1] : bitcoinData.honest[1]));
    const titles = ['All links agree', 'Block 2 points to the old hash', 'Chain tip rejected', 'Links rebuilt; work still missing'];
    const detail = [
      'The payment data and every previous hash pointer match.',
      'Changing one character produced a new real SHA 256 digest.',
      'The history fails the pointer check before consensus accepts it.',
      'Real Bitcoin would require new proof of work for the changed chain.'
    ];
    setText('.cstory-verdict-title', titles[stage]);
    setText('.cstory-verdict-copy', detail[stage]);
    setText('.cstory-verdictmark', stage === 1 || stage === 2 ? '×' : stage === 3 ? '!' : '✓');
  };

  const paintPos = () => {
    const slot = ['Choosing proposer', 'Atlas proposes the block', 'Atlas + Birch attest', 'A later checkpoint links back'];
    const finality = ['Not justified', 'Not justified', 'C1 justified', 'C1 finalized'];
    const nextFinality = ['Waiting for C1', 'Waiting for C1', 'C2 waiting', 'C2 justified'];
    const gauge = [0, 0, 80, 80];
    const status = ['waiting', 'included', 'included', 'included'];
    if (offline) {
      slot[3] = 'Next link stalls at 60%';
      finality[3] = 'C1 stays justified';
      nextFinality[3] = 'C2 not justified';
      gauge[3] = 60;
    }
    setText('.cstory-slot-title', slot[stage]);
    setText('.cstory-finality', finality[stage]);
    setText('.cstory-nextfinality', nextFinality[stage]);
    setText('.cstory-gaugevalue', `${gauge[stage]}%`);
    setText('.cstory-blockstatus', status[stage]);
    setText('.cstory-linklabel', stage === 3 ? offline ? '60% cannot link' : '80% link' : 'later link');
    root.style.setProperty('--vote', `${gauge[stage]}%`);
    root.dataset.offline = String(offline);
    if (offline) {
      captionTitle.textContent = 'Forty percent offline stalls the next link';
      captionCopy.textContent = 'The outage is spread across the whole modeled stake, not two named validators. At 60%, C2 cannot be justified, so C1 remains justified but not finalized.';
    }
  };

  const render = (next, announce = false) => {
    stage = Math.max(0, Math.min(3, next));
    if (kind === 'pos' && stage !== 3) offline = false;
    caption.setAttribute('aria-live', announce ? 'polite' : 'off');
    root.dataset.stage = String(stage);
    stepNumber.textContent = String(stage + 1).padStart(2, '0');
    captionNumber.textContent = String(stage + 1).padStart(2, '0');
    captionTitle.textContent = copy[stage][0];
    captionCopy.textContent = copy[stage][1];
    if (kind === 'bitcoin') paintBitcoin();
    else paintPos();
  };

  const schedule = () => {
    clearTimeout(timer);
    const playbackPaused = manuallyPaused || !visible || document.hidden;
    root.dataset.paused = String(playbackPaused);
    root.dataset.pauseReason = manuallyPaused ? 'manual' : !visible ? 'offscreen' : document.hidden ? 'hidden' : 'playing';
    if (playbackPaused) return;
    caption.setAttribute('aria-live', 'off');
    timer = setTimeout(() => {
      render(stage === 3 ? 0 : stage + 1);
      schedule();
    }, wait);
  };

  const setPaused = value => {
    manuallyPaused = value;
    pauseButton.textContent = manuallyPaused ? 'Play' : 'Pause';
    pauseButton.setAttribute('aria-pressed', String(manuallyPaused));
    caption.setAttribute('aria-live', manuallyPaused ? 'polite' : 'off');
    schedule();
  };

  pauseButton.addEventListener('click', () => setPaused(!manuallyPaused));
  root.querySelector('.cstory-next').addEventListener('click', () => {
    render(stage === 3 ? 0 : stage + 1, true);
    schedule();
  });
  root.querySelector('.cstory-replay').addEventListener('click', () => {
    offline = false;
    render(0, true);
    setPaused(false);
  });

  if (kind === 'bitcoin') {
    root.querySelector('.cstory-tamper').addEventListener('click', () => {
      render(1, true);
      setPaused(true);
    });
    root.querySelector('.cstory-rebuild').addEventListener('click', () => {
      render(3, true);
      setPaused(true);
    });
    computeBitcoin().catch(() => {
      root.querySelectorAll('[class*=cstory-hash], [class*=cstory-prev]').forEach(node => { node.textContent = 'SHA 256 unavailable'; });
    });
  } else {
    root.querySelector('.cstory-offline').addEventListener('click', () => {
      offline = true;
      render(3, true);
      setPaused(true);
    });
    root.querySelector('.cstory-restore').addEventListener('click', () => {
      offline = false;
      render(3, true);
      setPaused(true);
    });
    paintPos();
  }

  const observer = new IntersectionObserver(entries => {
    const entry = entries.find(candidate => candidate.target === root);
    if (!entry) return;
    visible = entry.isIntersecting;
    schedule();
  }, { threshold: [0, 0.28] });
  document.addEventListener('visibilitychange', schedule);
  observer.observe(root);
  render(0);
})();
