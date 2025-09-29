(function(){
  const form = document.getElementById('auditFilters');
  if(!form) return;

  form.querySelectorAll('input[type="search"]').forEach(input => {
    input.addEventListener('keydown', event => {
      if(event.key === 'Enter'){
        event.preventDefault();
        form.submit();
      }
    });
  });

  form.querySelector('select')?.addEventListener('change', () => form.submit());
})();
