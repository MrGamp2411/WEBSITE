(function () {
  const blocker = document.getElementById('deleteBlocker');
  if (!blocker) {
    return;
  }

  const cancelBtn = blocker.querySelector('.js-cancel-delete');
  const confirmBtn = blocker.querySelector('.js-confirm-delete');
  let targetForm = null;

  document.querySelectorAll('.js-delete-note').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      const id = btn.dataset.noteId;
      targetForm = document.getElementById(`delete-note-${id}`);
      blocker.hidden = false;
    });
  });

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      blocker.hidden = true;
      targetForm = null;
    });
  }

  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      if (targetForm) {
        targetForm.submit();
      }
    });
  }
})();
