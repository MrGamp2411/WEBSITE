(function () {
  function forceLowercase(event) {
    const currentValue = event.target.value;
    const lowerValue = currentValue.toLowerCase();

    if (currentValue === lowerValue) {
      return;
    }

    const { selectionStart, selectionEnd } = event.target;
    event.target.value = lowerValue;

    if (selectionStart !== null && selectionEnd !== null) {
      event.target.setSelectionRange(selectionStart, selectionEnd);
    }
  }

  function init() {
    const usernameInput = document.getElementById('username');
    if (!usernameInput) {
      return;
    }

    usernameInput.addEventListener('input', forceLowercase);
    usernameInput.addEventListener('blur', forceLowercase);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
