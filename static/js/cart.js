const form = document.getElementById('checkoutForm');
const submitBtn = document.querySelector('.place-order');

if (form && submitBtn) {
  form.addEventListener('submit', () => {
    submitBtn.disabled = true;
    submitBtn.style.display = 'none';
  });
}
