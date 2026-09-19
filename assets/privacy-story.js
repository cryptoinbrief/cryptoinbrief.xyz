(function () {
  'use strict';

  var path = location.pathname.toLowerCase();
  var coin = document.documentElement.getAttribute('data-coin') || '';
  var kind = path.indexOf('zero-knowledge') >= 0 ? 'zk' : path.indexOf('monero') >= 0 ? 'monero' : coin === 'zcash' || path.indexOf('zcash') >= 0 ? 'zcash' : '';
  if (!kind) return;

  var bay = document.querySelector('.bay');
  var lead = bay && bay.querySelector('.lead');
  if (!bay || !lead || bay.querySelector('.privacy-story')) return;

  var configs = {
    zcash: {
      accent: '#F4B728',
      logo: 'assets/coins/zcash.svg',
      logoAlt: 'Zcash',
      eyebrow: 'Shielded payment, slowed down',
      title: 'Watch one private note meet a public ledger',
      labels: [['Seal', 'commitment'], ['Prove', 'valid spend'], ['Publish', 'nullifier'], ['Reject', 'replay']],
      heads: ['The wallet seals a note', 'A proof carries the rules', 'The ledger records one fingerprint', 'The same note cannot spend twice'],
      copy: [
        'The amount and recipient stay inside the wallet. The chain receives a commitment that binds them without printing either value.',
        'A spend proof says the hidden note exists, belongs to the spender, and balances. This diagram does not perform a real Zcash proof.',
        'A nullifier is a public spent marker. It prevents reuse without naming the note that created it.',
        'A replay creates the same nullifier. The ledger has already seen it, so the second spend stops here.'
      ]
    },
    zk: {
      accent: '#627EEA',
      logo: '',
      logoAlt: 'Zero knowledge proof',
      eyebrow: 'Private credential, public answer',
      title: 'Prove an age rule without sending a birth date',
      labels: [['Enter', 'fictional data'], ['Build', 'predicate proof'], ['Check', 'proof only'], ['Reveal', 'one answer']],
      heads: ['Keep the private value local', 'Turn a rule into a proof', 'The verifier checks the proof', 'The answer arrives without the date'],
      copy: [
        'Use invented values only. A real age proof must bind the hidden age to a credential signed by a trusted issuer. Zero knowledge cannot make a self entered age true.',
        'The prover binds the hidden age and a fresh session challenge or nonce to the relying party and this session. A copied proof cannot answer a different challenge.',
        'The verifier receives a proof of the rule, not the private age or a date of birth.',
        'The result contains one fact: eligible or not eligible. Its truth still depends on the issuer that signed the source credential.'
      ]
    },
    monero: {
      accent: '#FF6600',
      logo: 'assets/coins/monero.svg',
      logoAlt: 'Monero',
      eyebrow: 'Ring signature, slowed down',
      title: 'A valid spend without exposing which member signed',
      labels: [['Gather', 'candidate keys'], ['Bind', 'one signature'], ['Verify', 'the whole ring'], ['Learn', 'valid, signer hidden']],
      heads: ['Several public keys enter the ring', 'One valid ring signature covers the set', 'The verifier checks the ring as a unit', 'Validity does not identify the sender'],
      copy: [
        'The ring contains the actual one time output public key plus decoy output public keys. Every candidate stays visually identical because the observer does not know the signer.',
        'The signer creates one proof tied to the full ring. The actual signing key is deliberately never highlighted.',
        'The network verifies that the ring signature is valid for one member. Key images, commitments, and range proofs enforce separate transaction rules.',
        'The result is not equal probability. It only means this signature does not reveal which ring member signed.'
      ]
    }
  };

  var c = configs[kind];
  var root = document.createElement('section');
  root.className = 'privacy-story ps-' + kind;
  root.setAttribute('aria-label', c.title);
  root.style.setProperty('--ps-accent', c.accent);
  root.dataset.phase = '0';
  root.dataset.playing = 'false';

  function node(cls, label, detail, logo) {
    return '<div class="ps-node ' + cls + '">' + (logo ? '<img src="' + c.logo + '" alt="">' : '') + '<strong>' + label + '</strong><small>' + detail + '</small></div>';
  }

  function scene() {
    if (kind === 'zcash') {
      return '<div class="ps-scene">' +
        node('ps-wallet', 'Private wallet', 'amount + recipient', true) +
        node('ps-proof', 'Spend circuit', 'rules checked', false) +
        node('ps-ledger', 'Public ledger', 'commitment + nullifier', false) +
        '<i class="ps-wire ps-wire-a"></i><i class="ps-wire ps-wire-b"></i>' +
        '<i class="ps-packet" aria-hidden="true"></i>' +
        '<div class="ps-status ps-recorded is-good">NULLIFIER RECORDED</div><div class="ps-status is-bad">REPLAY REJECTED</div><div class="ps-status ps-fresh is-good">FRESH NULLIFIER ACCEPTED</div>' +
        '</div>';
    }
    if (kind === 'zk') {
      return '<div class="ps-scene">' +
        '<div class="ps-inputs"><label class="ps-field">Fictional age<input class="ps-age" type="number" inputmode="numeric" min="1" max="120" value="24" aria-label="Fictional age"></label><label class="ps-field">Fictional session nonce<input class="ps-nonce" type="text" maxlength="16" value="demo4821" aria-label="Fictional session nonce"></label></div>' +
        node('ps-credential', 'Issuer signed credential', 'age stays hidden', false) +
        node('ps-prover', 'Proof builder', 'age ≥ 18 + session', false) +
        node('ps-verifier', 'Verifier', 'proof only', false) +
        '<i class="ps-wire ps-wire-a"></i><i class="ps-wire ps-wire-b"></i>' +
        '<i class="ps-packet" aria-hidden="true">π</i>' +
        '<div class="ps-status is-good"><span class="ps-result">ELIGIBLE: YES</span><br>AGE: HIDDEN</div>' +
        '</div>';
    }
    var candidates = '';
    for (var i = 0; i < 5; i += 1) candidates += '<span class="ps-candidate"><img src="' + c.logo + '" alt=""></span>';
    return '<div class="ps-scene"><div class="ps-ring">' + candidates + '<span class="ps-ring-core">one signer<br>not identified</span></div>' +
      node('ps-verifier', 'Network verifier', 'checks whole ring', false) +
      '<i class="ps-wire"></i><i class="ps-packet" aria-hidden="true">SIG</i>' +
      '<div class="ps-status is-good">VALID SIGNATURE</div><div class="ps-status">SIGNER: UNRESOLVED</div><div class="ps-status ps-invalid is-bad">TAMPERED: REJECTED</div></div>';
  }

  var steps = '';
  c.labels.forEach(function (label, index) {
    steps += '<button class="ps-step" type="button" data-step="' + index + '"' + (index === 0 ? ' aria-current="step"' : '') + '><b>0' + (index + 1) + ' ' + label[0] + '</b><span>' + label[1] + '</span></button>';
  });

  var brand = kind === 'zk' ? '<span class="ps-zkmark" aria-hidden="true"><i></i></span><span class="sr">Zero knowledge proof</span>' : '<img src="' + c.logo + '" alt="' + c.logoAlt + '">';
  root.innerHTML = '<div class="ps-head"><span class="ps-brand">' + brand + '</span><div><p class="ps-eyebrow">' + c.eyebrow + '</p><h2 class="ps-title">' + c.title + '</h2></div><span class="ps-live"><i></i><span>auto story</span></span></div>' +
    '<div class="ps-progress" role="tablist" aria-label="Animation stages">' + steps + '</div>' +
    '<div class="ps-stage">' + scene() + '<div class="ps-copy" aria-live="off"><span class="ps-stage-no">Stage 01</span><h3>' + c.heads[0] + '</h3><p>' + c.copy[0] + '</p><small class="ps-caveat">Conceptual sequence. Labels describe the idea, not production cryptography.</small></div></div>' +
    '<div class="ps-controls"><button class="ps-primary ps-pause" type="button">Pause</button><button class="ps-replay" type="button">Replay</button><button class="ps-next" type="button">Next stage</button>' + (kind === 'zcash' ? '<button class="ps-choice" type="button">Use a fresh note</button>' : kind === 'monero' ? '<button class="ps-choice" type="button">Tamper signature</button>' : '') + '<span class="ps-count">01 / 04</span></div>';

  lead.insertAdjacentElement('afterend', root);

  var phase = 0;
  var timer = 0;
  var inView = false;
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var manuallyPaused = false;
  var phaseButtons = Array.prototype.slice.call(root.querySelectorAll('.ps-step'));
  var pauseButton = root.querySelector('.ps-pause');
  var copyHead = root.querySelector('.ps-copy h3');
  var copyText = root.querySelector('.ps-copy p');
  var stageNumber = root.querySelector('.ps-stage-no');
  var counter = root.querySelector('.ps-count');
  var choiceButton = root.querySelector('.ps-choice');
  var choice = '';

  function updateResult() {
    if (kind !== 'zk') return;
    var input = root.querySelector('.ps-age');
    var age = Math.max(1, Math.min(120, parseInt(input.value, 10) || 1));
    input.value = age;
    root.querySelector('.ps-result').textContent = 'ELIGIBLE: ' + (age >= 18 ? 'YES' : 'NO');
    var status = root.querySelector('.ps-status');
    status.classList.toggle('is-good', age >= 18);
    status.classList.toggle('is-bad', age < 18);
  }

  function show(next, announce) {
    phase = (next + 4) % 4;
    root.dataset.phase = '-1';
    void root.offsetWidth;
    root.dataset.phase = String(phase);
    phaseButtons.forEach(function (button, index) {
      if (index === phase) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    stageNumber.textContent = 'Stage 0' + (phase + 1);
    counter.textContent = '0' + (phase + 1) + ' / 04';
    if (kind === 'zcash' && phase === 3 && choice === 'fresh') {
      copyHead.textContent = 'A fresh note creates a fresh nullifier';
      copyText.textContent = 'The ledger has not seen this spent marker. The teaching model accepts it and records the new nullifier.';
    } else if (kind === 'monero' && phase >= 2 && choice === 'tampered') {
      copyHead.textContent = 'A changed signature fails verification';
      copyText.textContent = 'Change one modeled signature value and the ring check fails. Rejection still reveals nothing about which member would have signed a valid spend.';
    } else {
      copyHead.textContent = c.heads[phase];
      copyText.textContent = c.copy[phase];
    }
    copyHead.parentElement.setAttribute('aria-live', announce ? 'polite' : 'off');
    if (kind === 'zk') updateResult();
  }

  function clearTimer() {
    if (timer) window.clearInterval(timer);
    timer = 0;
  }

  function canPlay() {
    return inView && !document.hidden && !manuallyPaused;
  }

  function sync() {
    clearTimer();
    var playing = canPlay();
    root.dataset.playing = String(playing);
    pauseButton.textContent = manuallyPaused ? 'Play' : 'Pause';
    if (playing) timer = window.setInterval(function () { show(phase + 1, false); }, reduced ? 3200 : 2600);
  }

  phaseButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      show(parseInt(button.dataset.step, 10), true);
      sync();
    });
  });

  pauseButton.addEventListener('click', function () {
    manuallyPaused = !manuallyPaused;
    sync();
  });

  root.querySelector('.ps-replay').addEventListener('click', function () {
    manuallyPaused = false;
    show(0, true);
    sync();
  });

  root.querySelector('.ps-next').addEventListener('click', function () {
    show(phase + 1, true);
    sync();
  });

  if (choiceButton) {
    choiceButton.addEventListener('click', function () {
      if (kind === 'zcash') {
        choice = choice === 'fresh' ? '' : 'fresh';
        root.dataset.choice = choice;
        choiceButton.textContent = choice === 'fresh' ? 'Replay same note' : 'Use a fresh note';
        show(3, true);
      } else {
        choice = choice === 'tampered' ? '' : 'tampered';
        root.dataset.choice = choice;
        choiceButton.textContent = choice === 'tampered' ? 'Restore valid signature' : 'Tamper signature';
        show(2, true);
      }
      sync();
    });
  }

  if (kind === 'zk') {
    root.querySelector('.ps-age').addEventListener('input', updateResult);
    root.querySelector('.ps-nonce').addEventListener('input', function (event) {
      event.target.value = event.target.value.replace(/[^a-zA-Z0-9]/g, '').slice(0, 16);
    });
  }

  document.addEventListener('visibilitychange', sync);
  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.target !== root) return;
        inView = entry.isIntersecting;
        sync();
      });
    }, { threshold: 0.32 });
    observer.observe(root);
  } else {
    inView = true;
    sync();
  }
  show(0, false);
}());
