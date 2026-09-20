(function () {
  'use strict';

  if (window.__support) return;

  var root = document.documentElement;
  var rtl = root.dir === 'rtl' || root.lang === 'ar';
  var labels = rtl ? {
    trigger: 'تبرع',
    title: 'ادعم Crypto in Brief',
    intro: 'ساعد في إبقاء الشروحات والتجارب متاحة للجميع.',
    choose: 'اختر العملة',
    address: 'عنوان الاستلام',
    copy: 'نسخ العنوان',
    copied: 'تم نسخ عنوان',
    failed: 'تعذر النسخ. حدد العنوان وانسخه يدويا.',
    close: 'إغلاق',
    referrals: 'روابط الإحالة',
    open: 'فتح'
  } : {
    trigger: 'Donate',
    title: 'Support Crypto in Brief',
    intro: 'Help keep the explainers and working labs available to everyone.',
    choose: 'Choose a currency',
    address: 'Receiving address',
    copy: 'Copy address',
    copied: 'Copied',
    failed: 'Copy failed. Select the address and copy it manually.',
    close: 'Close',
    referrals: 'Referral links',
    open: 'Open'
  };

  var currencies = [
    {
      code: 'XMR',
      name: 'Monero',
      network: 'Monero network',
      address: '49BWStdJJVEfPRDQTmCtrT39QSqXNWLUGNvTzU7cMfsMHTG1ozR1YFQPCKb65oduji5isbVAowiwVFPpseHv9Dg3875rB9G',
      image: 'assets/coins/monero.svg'
    },
    {
      code: 'BTC',
      name: 'Bitcoin',
      network: 'Bitcoin network',
      address: 'bc1q7avt57ekp002lzq2untsr5lpqy9hsfqudf7a5h',
      image: 'assets/coins/bitcoin.svg'
    },
    {
      code: 'LTC',
      name: 'Litecoin',
      network: 'Litecoin network',
      address: 'ltc1qrvecg74m4elgm9j2el78zgau5a4l3x245jwqmj'
    },
    {
      code: 'ZEC',
      name: 'Zcash',
      network: 'Zcash Unified Address',
      address: 'u1hpydpv0n36jvucwevy6477auq5ml5wjgzfrwq20xsau78mj9x576fkx7cd2q23f35lr0wctznsj27tnxh0anujlcdn45sqsvqm0kshl09982f4tmpa64npzezu5m3d7wm4vv6uqjlvkdda9lzavn8yqfgmzaykgcxt5lqmme5qr5epwt',
      image: 'assets/coins/zcash.svg'
    },
    {
      code: 'DASH',
      name: 'Dash',
      network: 'Dash network',
      address: 'XjZo388Ct5tssNwC9BDbzXqC52YXqyUPsz'
    },
    {
      code: 'ETH',
      name: 'Ethereum',
      network: 'Ethereum network',
      address: '0x56102e5dc2bCE0ab5766e87a2363cea93FbB7D4d',
      image: 'assets/coins/ethereum.svg'
    },
    {
      code: 'SOL',
      name: 'Solana',
      network: 'Solana network',
      address: '8jUUGAtcTW7ZxGMUPtuJGsmyep5oxmcrBENFZ8TDoiBm',
      image: 'assets/coins/solana.svg'
    }
  ];

  var referrals = [
    ['Bybit', 'https://www.bybit.com/invite?ref=MWBL9%230&medium=referral&utm_campaign=evergreen'],
    ['Binance', 'https://www.binance.com/referral/earn-together/refer2earn-usdc/claim?hl=en&ref=GRO_28502_WQILP&utm_source=referral_entrance']
  ];

  function make(tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (text != null) element.textContent = text;
    return element;
  }

  function addMark(target, currency, compact) {
    if (currency.image) {
      var image = make('img', 'support-coin-image');
      image.src = currency.image;
      image.alt = '';
      image.width = compact ? 22 : 34;
      image.height = compact ? 22 : 34;
      target.appendChild(image);
    } else {
      target.appendChild(make('span', 'support-coin-type', currency.code));
    }
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(function () {
        return true;
      }).catch(function () {
        return false;
      });
    }
    return Promise.resolve(false);
  }

  function selectAddress(element) {
    var selection = window.getSelection();
    if (!selection) return;
    var range = document.createRange();
    range.selectNodeContents(element);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  var target = document.querySelector('.site-nav') || document.querySelector('.site-header');
  if (!target) return;

  var trigger = make('button', 'support-trigger', labels.trigger);
  trigger.type = 'button';
  trigger.setAttribute('aria-haspopup', 'dialog');

  if (target.classList.contains('site-nav')) {
    var themeButton = target.querySelector('.theme-button');
    target.insertBefore(trigger, themeButton || null);
  } else {
    var switcher = target.querySelector('.switch');
    target.insertBefore(trigger, switcher || null);
  }

  var dialog = make('dialog', 'support-dialog');
  dialog.setAttribute('aria-labelledby', 'support-title');
  var sheet = make('div', 'support-sheet');
  var heading = make('header', 'support-heading');
  var headingCopy = make('div');
  var kicker = make('span', 'support-kicker', 'Crypto in Brief');
  var title = make('h2', '', labels.title);
  title.id = 'support-title';
  var intro = make('p', '', labels.intro);
  headingCopy.appendChild(kicker);
  headingCopy.appendChild(title);
  headingCopy.appendChild(intro);
  var closeButton = make('button', 'support-close', labels.close);
  closeButton.type = 'button';
  heading.appendChild(headingCopy);
  heading.appendChild(closeButton);

  var body = make('div', 'support-body');
  var tabs = make('div', 'support-tabs');
  tabs.setAttribute('role', 'tablist');
  tabs.setAttribute('aria-label', labels.choose);
  var panel = make('section', 'support-panel');
  panel.id = 'support-panel';
  panel.setAttribute('role', 'tabpanel');
  panel.tabIndex = 0;

  var identity = make('div', 'support-identity');
  var identityMark = make('span', 'support-identity-mark');
  var identityCopy = make('span', 'support-identity-copy');
  var coinName = make('strong');
  var network = make('span');
  identityCopy.appendChild(coinName);
  identityCopy.appendChild(network);
  identity.appendChild(identityMark);
  identity.appendChild(identityCopy);

  var addressLabel = make('span', 'support-address-label', labels.address);
  var address = make('code', 'support-address');
  address.dir = 'ltr';
  var copyButton = make('button', 'support-copy', labels.copy);
  copyButton.type = 'button';
  var status = make('p', 'support-status');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  var addressBlock = make('div', 'support-address-block');
  addressBlock.appendChild(addressLabel);
  addressBlock.appendChild(address);
  addressBlock.appendChild(copyButton);
  addressBlock.appendChild(status);
  panel.appendChild(identity);
  panel.appendChild(addressBlock);
  body.appendChild(tabs);
  body.appendChild(panel);

  var referralSection = make('section', 'support-referrals');
  referralSection.appendChild(make('h3', '', labels.referrals));
  var referralLinks = make('div', 'support-referral-links');
  referrals.forEach(function (referral) {
    var link = make('a', '', referral[0] + ' ' + labels.open);
    link.href = referral[1];
    link.target = '_blank';
    link.rel = 'sponsored noopener noreferrer';
    referralLinks.appendChild(link);
  });
  referralSection.appendChild(referralLinks);
  referralSection.appendChild(make('p', 'support-disclosure', 'These are referral links. I may receive a benefit if you use them.'));

  sheet.appendChild(heading);
  sheet.appendChild(body);
  sheet.appendChild(referralSection);
  dialog.appendChild(sheet);
  document.body.appendChild(dialog);

  var buttons = [];
  var selected = 0;
  var returnFocus = null;

  function selectCurrency(index, focus) {
    selected = index;
    var currency = currencies[index];
    buttons.forEach(function (button, buttonIndex) {
      var current = buttonIndex === index;
      button.setAttribute('aria-selected', current ? 'true' : 'false');
      button.tabIndex = current ? 0 : -1;
    });
    identityMark.replaceChildren();
    addMark(identityMark, currency, false);
    coinName.textContent = currency.name + ' · ' + currency.code;
    network.textContent = currency.network;
    address.textContent = currency.address;
    address.setAttribute('aria-label', currency.code + ' ' + labels.address);
    copyButton.disabled = false;
    copyButton.textContent = labels.copy;
    status.textContent = '';
    panel.setAttribute('aria-labelledby', buttons[index].id);
    if (focus) buttons[index].focus();
  }

  currencies.forEach(function (currency, index) {
    var button = make('button', 'support-tab');
    button.type = 'button';
    button.id = 'support-tab-' + currency.code.toLowerCase();
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-controls', panel.id);
    button.setAttribute('data-currency', currency.code);
    var mark = make('span', 'support-tab-mark');
    addMark(mark, currency, true);
    var copy = make('span', 'support-tab-copy');
    copy.appendChild(make('strong', '', currency.code));
    copy.appendChild(make('small', '', currency.name));
    button.appendChild(mark);
    button.appendChild(copy);
    button.addEventListener('click', function () {
      selectCurrency(index, false);
    });
    button.addEventListener('keydown', function (event) {
      var next = null;
      if (event.key === 'ArrowDown' || event.key === 'ArrowRight') next = (index + 1) % buttons.length;
      if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') next = (index - 1 + buttons.length) % buttons.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = buttons.length - 1;
      if (next != null) {
        event.preventDefault();
        selectCurrency(next, true);
      }
    });
    buttons.push(button);
    tabs.appendChild(button);
  });

  copyButton.addEventListener('click', function () {
    var currency = currencies[selected];
    copyText(currency.address).then(function (copied) {
      if (copied) {
        status.textContent = labels.copied + ' ' + currency.code;
        return;
      }
      status.textContent = labels.failed;
      selectAddress(address);
    });
  });

  function openDialog() {
    returnFocus = document.activeElement;
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    requestAnimationFrame(function () {
      buttons[selected].focus();
    });
  }

  function closeDialog() {
    if (typeof dialog.close === 'function') dialog.close();
    else {
      dialog.removeAttribute('open');
      if (returnFocus && returnFocus.focus) returnFocus.focus();
    }
  }

  trigger.addEventListener('click', openDialog);
  closeButton.addEventListener('click', closeDialog);
  dialog.addEventListener('close', function () {
    if (returnFocus && returnFocus.focus) returnFocus.focus();
  });
  dialog.addEventListener('click', function (event) {
    if (event.target === dialog) closeDialog();
  });

  selectCurrency(0, false);
  window.__support = {
    dialog: dialog,
    currencies: currencies.slice(),
    referrals: referrals.slice(),
    open: openDialog,
    close: closeDialog
  };
})();
