(function(){
  const input = document.getElementById('barsSearch');
  if (!input) return;
  const tbody = document.querySelector('.bars-table tbody');
  if (!tbody) return;

  const rows = Array.from(tbody.rows);
  const normalize = (value) => (value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();

  const applyFilter = () => {
    const query = normalize(input.value);
    rows.forEach((row) => {
      const nameCell = row.cells && row.cells[1] ? row.cells[1].textContent : '';
      const match = query === '' || normalize(nameCell).includes(query);
      row.style.display = match ? '' : 'none';
    });
  };

  const debounce = (fn, ms) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(null, args), ms);
    };
  };

  const runFilter = debounce(applyFilter, 120);

  input.addEventListener('input', runFilter);
  document.querySelector('.bars-search .clear')?.addEventListener('click', () => {
    input.value = '';
    applyFilter();
    input.focus();
  });

  const params = new URLSearchParams(window.location.search);
  const initialQuery = params.get('q');
  if (initialQuery) {
    input.value = initialQuery;
    applyFilter();
  }

  const blocker = document.getElementById('deleteBlocker');
  const cancelBtn = document.querySelector('.js-cancel-delete');
  const confirmBtn = document.querySelector('.js-confirm-delete');
  let targetForm = null;

  document.querySelectorAll('.js-delete-bar').forEach((trigger) => {
    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      const { barId } = trigger.dataset;
      targetForm = document.getElementById(`delete-bar-${barId}`);
      if (blocker) blocker.hidden = false;
    });
  });

  cancelBtn?.addEventListener('click', () => {
    if (blocker) blocker.hidden = true;
    targetForm = null;
  });

  confirmBtn?.addEventListener('click', () => {
    if (targetForm) targetForm.submit();
  });
})();
