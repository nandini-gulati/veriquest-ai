/* Small, DOM-safe enhancements for the stock Chainlit interface. */
(function () {
  function findComposer() {
    return document.querySelector('#chat-input textarea, textarea#chat-input, textarea');
  }

  function addBrand() {
    const header = document.querySelector('#header') || document.querySelector('header') || document.querySelector('[class*="header"]');
    if (!header || header.querySelector('.vq-brand')) return;
    const brand = document.createElement('div');
    brand.className = 'vq-brand';
    brand.setAttribute('aria-label', 'VeriQuest AI');
    brand.innerHTML = '<span class="vq-brand__mark" aria-hidden="true">V</span><span>VeriQuest AI</span><span class="vq-brand__tag">Research with sources</span>';
    header.prepend(brand);
  }

  function refineComposer() {
    const input = findComposer();
    if (!input) return;
    input.setAttribute('placeholder', 'Ask anything…');
    const composer = input.closest('form') || input.closest('[class*="MuiOutlinedInput-root"], [class*="MuiInputBase-root"]')?.parentElement;
    if (composer && !composer.parentElement.querySelector('.vq-composer-note')) {
      const note = document.createElement('div');
      note.className = 'vq-composer-note';
      note.textContent = 'VeriQuest AI searches for sources before it answers';
      composer.insertAdjacentElement('afterend', note);
    }
  }

  function enhance() {
    document.documentElement.dataset.veriquest = 'true';
    addBrand();
    refineComposer();
  }

  document.addEventListener('DOMContentLoaded', enhance);
  new MutationObserver(enhance).observe(document.documentElement, { childList: true, subtree: true });
  setInterval(enhance, 1500);
})();
