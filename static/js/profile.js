document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('profile-form');
  if (!form) return;
  const fields = form.querySelectorAll('input, select');

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
