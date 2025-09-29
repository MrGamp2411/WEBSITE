(function () {
  const searchForm = document.querySelector('.menu-search');
  const input = document.getElementById('categorySearch');
  const clearBtn = document.querySelector('.menu-search .clear');
  const tbody = document.querySelector('.menu-table tbody');

  searchForm?.addEventListener('submit', (event) => {
    event.preventDefault();
  });

  if (!input) return;

  const rows = tbody ? Array.from(tbody.rows) : [];
  const normalise = (value) => (value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();

  const applyFilter = () => {
    const query = normalise(input.value);
    rows.forEach((row) => {
      const nameCell = row.cells && row.cells[1] ? row.cells[1].textContent : '';
      const isMatch = !query || normalise(nameCell).includes(query);
      row.style.display = isMatch ? '' : 'none';
    });
  };

  const debounce = (fn, ms) => {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn.apply(null, args), ms);
    };
  };

  const debouncedFilter = debounce(applyFilter, 120);

  input.addEventListener('input', debouncedFilter);
  clearBtn?.addEventListener('click', () => {
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

  document.querySelectorAll('form[data-confirm-message]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.dataset.confirmMessage;
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
})();
