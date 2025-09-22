document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('profile-form');
  if (!form) return;
  const fields = form.querySelectorAll('input, select');
  const usernameInput = document.getElementById('username');

  if (usernameInput) {
    const forceLowercase = event => {
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
    };

    usernameInput.addEventListener('input', forceLowercase);
    usernameInput.addEventListener('blur', forceLowercase);
  }

  form.querySelectorAll('.edit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.parentElement.querySelector('input, select');
      if (input) {
        input.disabled = false;
        input.focus();
      }
    });
  });

  form.addEventListener('submit', () => {
    fields.forEach(el => {
      el.disabled = false;
    });
  });
});
