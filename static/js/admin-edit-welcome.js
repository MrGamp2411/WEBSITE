(function(){
  function toggleTranslations() {
    document.querySelectorAll('.translation-toggle').forEach((button) => {
      button.addEventListener('click', () => {
        const targetId = button.getAttribute('data-translation-target');
        if (!targetId) return;
        const target = document.getElementById(targetId);
        if (!target) return;
        const expanded = button.getAttribute('aria-expanded') === 'true';
        const nextState = !expanded;
        button.setAttribute('aria-expanded', String(nextState));
        if (nextState) {
          target.removeAttribute('hidden');
        } else {
          target.setAttribute('hidden', '');
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', toggleTranslations);
})();
