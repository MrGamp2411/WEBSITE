document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.password-wrapper').forEach(wrapper => {
    const input = wrapper.querySelector('input');
    const toggle = wrapper.querySelector('.toggle-password');
    const warning = wrapper.parentElement.querySelector('.caps-warning');
    if (toggle && input) {
      const showLabel = toggle.dataset.showLabel || 'Show password';
      const hideLabel = toggle.dataset.hideLabel || 'Hide password';
      toggle.addEventListener('click', () => {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        toggle.setAttribute('aria-label', isPassword ? hideLabel : showLabel);
      });
      input.addEventListener('keyup', e => {
        if (warning) warning.hidden = !e.getModifierState('CapsLock');
      });
      input.addEventListener('blur', () => {
        if (warning) warning.hidden = true;
      });
    }
  });
  const password = document.getElementById('password');
  const confirm = document.getElementById('confirm_password');
  if (password && confirm) {
    const mismatchMessage = confirm.dataset.mismatchMessage || 'Passwords must match';
    const validate = () => {
      confirm.setCustomValidity(confirm.value !== password.value ? mismatchMessage : '');
    };
    password.addEventListener('input', validate);
    confirm.addEventListener('input', validate);
  }
});
