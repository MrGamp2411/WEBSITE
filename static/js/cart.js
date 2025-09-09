// Keeps the mobile Place Order button fixed at the bottom
// but lets it stop above the site footer

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.querySelector('.btn-primary.place-order');
  const footer = document.querySelector('.site-footer');
  if (!btn || !footer) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        btn.classList.add('stop');
      } else {
        btn.classList.remove('stop');
      }
    });
  });

  observer.observe(footer);
});
