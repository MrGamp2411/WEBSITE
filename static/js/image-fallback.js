(function () {
  const images = document.querySelectorAll('img[data-fallback-src]');
  if (!images.length) {
    return;
  }

  images.forEach((img) => {
    const fallbackSrc = img.dataset.fallbackSrc;
    if (!fallbackSrc) {
      return;
    }

    const applyFallback = () => {
      if (img.dataset.fallbackApplied === 'true') {
        return;
      }
      img.dataset.fallbackApplied = 'true';
      img.src = fallbackSrc;
    };

    img.addEventListener('error', applyFallback, { once: true });

    if (img.complete && img.naturalWidth === 0) {
      applyFallback();
    }
  });
})();
