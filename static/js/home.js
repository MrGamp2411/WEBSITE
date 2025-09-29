(function () {
  const images = document.querySelectorAll('img[data-fallback-src]');
  images.forEach((img) => {
    const fallbackSrc = img.dataset.fallbackSrc;
    if (!fallbackSrc) {
      return;
    }

    const handleError = () => {
      if (img.dataset.fallbackApplied === 'true') {
        return;
      }
      img.dataset.fallbackApplied = 'true';
      img.src = fallbackSrc;
    };

    img.addEventListener('error', handleError, { once: true });

    if (img.complete && img.naturalWidth === 0) {
      handleError();
    }
  });
})();
