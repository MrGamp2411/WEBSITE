document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.password-wrapper').forEach(wrapper => {
    const input = wrapper.querySelector('input');
    const toggle = wrapper.querySelector('.toggle-password');
    const warning = wrapper.parentElement.querySelector('.caps-warning');
    if (toggle && input) {
      toggle.addEventListener('click', () => {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        toggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
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
    const validate = () => {
      confirm.setCustomValidity(confirm.value !== password.value ? 'Passwords must match' : '');
    };
    password.addEventListener('input', validate);
    confirm.addEventListener('input', validate);
  }
});
