(function () {
  const barDetail = document.querySelector('.bar-detail');
  if (!barDetail) {
    return;
  }

  const pausedValue = barDetail.dataset.orderingPaused;
  if (typeof pausedValue !== 'undefined') {
    window.orderingPaused = pausedValue === 'true';
  }
})();

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

(function () {
  const directionsLink = document.querySelector('.bar-directions');
  if (!directionsLink) {
    return;
  }

  const appleUrl = directionsLink.getAttribute('data-apple-url');
  const googleUrl = directionsLink.getAttribute('data-google-url');
  const userAgent = window.navigator.userAgent || '';
  const platform = window.navigator.platform || '';
  const isAppleDevice = /iPad|iPhone|iPod/.test(userAgent) ||
    (platform === 'MacIntel' && typeof window.navigator.standalone !== 'undefined');

  if (isAppleDevice && appleUrl) {
    directionsLink.setAttribute('href', appleUrl);
  } else if (googleUrl) {
    directionsLink.setAttribute('href', googleUrl);
  }
})();
