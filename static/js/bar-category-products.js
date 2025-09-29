(function () {
  const buttons = document.querySelectorAll('.js-confirm-product-delete');
  if (!buttons.length) {
    return;
  }

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      const formId = button.dataset.formId;
      if (!formId) {
        return;
      }

      const confirmMessage = button.dataset.confirmMessage || '';
      const targetForm = document.getElementById(formId);
      if (!targetForm) {
        return;
      }

      if (!confirmMessage || window.confirm(confirmMessage)) {
        targetForm.submit();
      }
    });
  });
})();
