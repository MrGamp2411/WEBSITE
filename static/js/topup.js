(function () {
  const form = document.getElementById('topupForm');
  if (!form) {
    return;
  }

  const amountInput = document.getElementById('amount');
  if (!amountInput) {
    return;
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  if (!submitBtn) {
    return;
  }

  const invalidAmountMessage = form.dataset.invalidAmountMessage || 'Invalid amount';
  const errorMessage = form.dataset.errorMessage || 'Unable to start top-up';

  form.querySelectorAll('button[data-amount]').forEach((button) => {
    button.addEventListener('click', () => {
      amountInput.value = button.dataset.amount || '';
    });
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submitBtn.disabled) {
      return;
    }

    const amount = parseFloat(amountInput.value);
    const minAmount = parseFloat(amountInput.min) || 0;
    if (!Number.isFinite(amount) || amount < minAmount) {
      window.alert(invalidAmountMessage);
      return;
    }

    submitBtn.disabled = true;
    const originalDisplay = submitBtn.style.display;
    submitBtn.style.display = 'none';

    try {
      const response = await fetch('/api/topup/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount })
      });

      if (response.ok) {
        const data = await response.json();
        if (data && data.paymentPageUrl) {
          window.location.replace(data.paymentPageUrl);
          return;
        }
      }

      window.alert(errorMessage);
      submitBtn.disabled = false;
      submitBtn.style.display = originalDisplay;
    } catch (error) {
      window.alert(errorMessage);
      submitBtn.disabled = false;
      submitBtn.style.display = originalDisplay;
    }
  });
})();
