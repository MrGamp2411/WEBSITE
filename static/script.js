document.addEventListener('DOMContentLoaded', function() {
  const searchInput = document.getElementById('barSearch');
  if (searchInput) {
    searchInput.addEventListener('keyup', function() {
      const term = this.value.toLowerCase();
      document.querySelectorAll('.bar-card').forEach(card => {
        const name = card.dataset.name;
        const address = card.dataset.address;
        card.style.display = (name.includes(term) || address.includes(term)) ? '' : 'none';
      });
    });
  }

  const toggle = document.getElementById('themeToggle');
  if (toggle) {
    toggle.addEventListener('click', function() {
      document.body.classList.toggle('dark-mode');
      const mode = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
      localStorage.setItem('theme', mode);
    });
    const stored = localStorage.getItem('theme');
    if (stored === 'dark') {
      document.body.classList.add('dark-mode');
    }
  }
});
