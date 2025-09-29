(function(){
  function init(){
    const form = document.querySelector('.admin-dashboard__clear-orders');
    if(!form) return;

    const message = form.dataset.confirmMessage || 'Delete all orders?';
    form.addEventListener('submit', (event) => {
      if(!window.confirm(message)){
        event.preventDefault();
      }
    });
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
