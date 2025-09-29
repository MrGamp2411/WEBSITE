document.addEventListener('DOMContentLoaded', () => {
  const displaySection = document.querySelector('.display-page');
  if (!displaySection) {
    return;
  }

  const barId = Number.parseInt(displaySection.dataset.barId, 10);
  if (!Number.isFinite(barId)) {
    return;
  }

  if (typeof initDisplay === 'function') {
    initDisplay(barId);
  }
});
