(function(){
  const searchForm = document.querySelector('.menu-search.js-prevent-submit');
  const input = document.getElementById('tableSearch');
  const clearBtn = document.querySelector('.menu-search .clear');
  const tbody = document.querySelector('.menu-table tbody');
  if(!input || !tbody) return;

  searchForm?.addEventListener('submit', event => {
    event.preventDefault();
  });

  const rows = Array.from(tbody.rows);
  const normalise = value => (value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();

  function applyFilter(){
    const query = normalise(input.value);
    rows.forEach(row => {
      const name = row.cells && row.cells[1] ? row.cells[1].textContent : '';
      const description = row.cells && row.cells[2] ? row.cells[2].textContent : '';
      const match = !query || normalise(name).includes(query) || normalise(description).includes(query);
      row.style.display = match ? '' : 'none';
    });
  }

  function debounce(callback, wait){
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => callback.apply(this, args), wait);
    };
  }

  const runFilter = debounce(applyFilter, 120);

  input.addEventListener('input', runFilter);
  clearBtn?.addEventListener('click', () => {
    input.value = '';
    applyFilter();
    input.focus();
  });

  const searchParams = new URLSearchParams(location.search);
  const query = searchParams.get('q');
  if(query){
    input.value = query;
    applyFilter();
  }

  const blocker = document.getElementById('deleteBlocker');
  const cancelBtn = document.querySelector('.js-cancel-delete');
  const confirmBtn = document.querySelector('.js-confirm-delete');
  let targetForm = null;

  document.querySelectorAll('.js-delete-table').forEach(button => {
    button.addEventListener('click', event => {
      event.preventDefault();
      const tableId = button.dataset.tableId;
      targetForm = document.getElementById('delete_' + tableId);
      if(blocker) blocker.hidden = false;
    });
  });

  cancelBtn?.addEventListener('click', () => {
    if(blocker) blocker.hidden = true;
    targetForm = null;
  });

  confirmBtn?.addEventListener('click', () => {
    targetForm?.submit();
  });
})();
