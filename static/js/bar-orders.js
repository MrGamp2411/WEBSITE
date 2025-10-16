(function(){
  function init(){
    const root = document.querySelector('.orders-page[data-bar-id]');
    if(!root) return;
    const barId = Number.parseInt(root.dataset.barId, 10);
    if(Number.isNaN(barId) || typeof window.initBartender !== 'function') return;

    window.initBartender(barId);

    const pauseToggle = document.getElementById('pause-ordering');
    const pauseUrl = root.dataset.pauseUrl;
    if(pauseToggle && pauseUrl){
      pauseToggle.addEventListener('change', () => {
        const headers = { 'Content-Type': 'application/json' };
        if (window.CSRF_TOKEN) {
          headers['X-CSRF-Token'] = window.CSRF_TOKEN;
        }
        fetch(pauseUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify({ paused: pauseToggle.checked })
        }).catch(() => {});
      });
    }
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
