(function(){
  const blocker = document.getElementById('ipBlocker');
  if (!blocker) return;

  const cancelBtn = blocker.querySelector('.js-cancel-ip');
  const confirmBtn = blocker.querySelector('.js-confirm-ip');
  let targetForm = null;

  document.querySelectorAll('.ip-block-delete').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!targetForm) {
        event.preventDefault();
        targetForm = form;
        blocker.hidden = false;
      }
    });
  });

  cancelBtn?.addEventListener('click', () => {
    blocker.hidden = true;
    targetForm = null;
  });

  confirmBtn?.addEventListener('click', () => {
    if (targetForm) {
      targetForm.submit();
    }
  });
})();
