(function(){
  function initOrderHistoryCounts(root) {
    const pendingGrid = root.querySelector('#pending-orders');
    const completedGrid = root.querySelector('#completed-orders');
    const pendingCount = root.querySelector('#pendingCount');
    const completedCount = root.querySelector('#completedCount');
    const pendingEmpty = root.querySelector('#pendingEmpty');
    const completedEmpty = root.querySelector('#completedEmpty');
    if (!pendingGrid || !completedGrid || !pendingCount || !completedCount) {
      return;
    }

    const update = () => {
      const pendingLength = pendingGrid.children.length;
      const completedLength = completedGrid.children.length;
      pendingCount.textContent = pendingLength;
      completedCount.textContent = completedLength;
      if (pendingEmpty) {
        pendingEmpty.classList.toggle('show', pendingLength === 0);
      }
      if (completedEmpty) {
        completedEmpty.classList.toggle('show', completedLength === 0);
      }
    };

    update();
    const observerConfig = { childList: true };
    const observer = new MutationObserver(update);
    observer.observe(pendingGrid, observerConfig);
    observer.observe(completedGrid, observerConfig);
  }

  function boot() {
    const root = document.querySelector('[data-order-history]');
    if (!root) return;

    const userIdRaw = root.dataset.userId || '';
    const userId = Number.parseInt(userIdRaw, 10);
    if (Number.isFinite(userId) && typeof window.initUser === 'function') {
      window.initUser(userId);
    }

    initOrderHistoryCounts(root);
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
