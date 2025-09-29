(function(){
  function normalize(value){
    return (value || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();
  }

  function init(){
    const input = document.getElementById('userSearch');
    const tbody = document.querySelector('.users-table tbody');
    if(!input || !tbody) return;

    const rows = Array.from(tbody.rows);

    function applyFilter(){
      const query = normalize(input.value);
      rows.forEach(row => {
        const name = row.cells && row.cells[0] ? row.cells[0].textContent : '';
        const email = row.cells && row.cells[1] ? row.cells[1].textContent : '';
        const match = !query || normalize(name).includes(query) || normalize(email).includes(query);
        row.style.display = match ? '' : 'none';
      });
    }

    function debounce(fn, delay){
      let timer;
      return function debounced(...args){
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
      };
    }

    const run = debounce(applyFilter, 120);
    input.addEventListener('input', run);

    const form = document.querySelector('.users-search');
    if(form){
      form.addEventListener('submit', (event) => {
        event.preventDefault();
      });
    }

    const clearButton = form ? form.querySelector('.clear') : document.querySelector('.users-search .clear');
    if(clearButton){
      clearButton.addEventListener('click', () => {
        input.value = '';
        applyFilter();
        input.focus();
      });
    }

    const qs = new URLSearchParams(window.location.search);
    const preset = qs.get('q');
    if(preset){
      input.value = preset;
      applyFilter();
    }
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
