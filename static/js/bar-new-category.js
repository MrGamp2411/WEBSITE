document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.translation-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const targetId = button.dataset.translationTarget;
      if (!targetId) return;

      const panel = document.getElementById(targetId);
      if (!panel) return;

      const isExpanded = button.getAttribute('aria-expanded') === 'true';
      const nextState = !isExpanded;
      button.setAttribute('aria-expanded', String(nextState));

      if (nextState) {
        panel.removeAttribute('hidden');
      } else {
        panel.setAttribute('hidden', '');
      }
    });
  });
});
