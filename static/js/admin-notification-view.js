(function(){
  const blocker = document.getElementById('deleteBlocker');
  if (!blocker) return;

  const cancelBtn = blocker.querySelector('.js-cancel-delete');
  const confirmBtn = blocker.querySelector('.js-confirm-delete');
  const deleteTrigger = document.querySelector('.js-delete-note');
  let targetForm = null;

  deleteTrigger?.addEventListener('click', (event) => {
    event.preventDefault();
    const { noteId } = deleteTrigger.dataset;
    targetForm = document.getElementById(`delete-note-${noteId}`);
    blocker.hidden = false;
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
