(function () {
  function normalize(value) {
    return (value || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();
  }

  function debounce(fn, delay) {
    let timeoutId;
    return (...args) => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      timeoutId = setTimeout(() => fn.apply(null, args), delay);
    };
  }

  function initPaymentsFilter() {
    const input = document.getElementById('paymentsSearch');
    const tableBody = document.querySelector('.payments-table tbody');
    if (!input || !tableBody) {
      return;
    }

    const rows = Array.from(tableBody.rows);

    function applyFilter() {
      const query = normalize(input.value);
      rows.forEach((row) => {
        const numberCell = row.cells && row.cells[0] ? row.cells[0].textContent : '';
        const nameCell = row.cells && row.cells[1] ? row.cells[1].textContent : '';
        const matches =
          !query ||
          normalize(nameCell).includes(query) ||
          normalize(numberCell).includes(query);
        row.style.display = matches ? '' : 'none';
      });
    }

    const runFilter = debounce(applyFilter, 120);
    input.addEventListener('input', runFilter);

    const clearButton = document.querySelector('.payments-search .clear');
    if (clearButton) {
      clearButton.addEventListener('click', () => {
        input.value = '';
        applyFilter();
        input.focus();
      });
    }

    const params = new URLSearchParams(window.location.search);
    const existingQuery = params.get('q');
    if (existingQuery) {
      input.value = existingQuery;
      applyFilter();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPaymentsFilter);
  } else {
    initPaymentsFilter();
  }
})();
