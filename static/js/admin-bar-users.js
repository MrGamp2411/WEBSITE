(function () {
  const searchForm = document.querySelector('.users-search');
  if (searchForm) {
    searchForm.addEventListener('submit', (event) => {
      event.preventDefault();
    });
  }

  const input = document.getElementById('userSearch');
  const tableBody = document.querySelector('.users-table tbody');

  if (input && tableBody) {
    const rows = Array.from(tableBody.rows);

    const normalise = (value) => {
      return (value || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim();
    };

    const applyFilter = () => {
      const query = normalise(input.value);
      rows.forEach((row) => {
        const nameCell = row.cells[0] ? row.cells[0].textContent : '';
        const emailCell = row.cells[1] ? row.cells[1].textContent : '';
        const matches = !query || normalise(nameCell).includes(query) || normalise(emailCell).includes(query);
        row.style.display = matches ? '' : 'none';
      });
    };

    const debounce = (fn, delay) => {
      let timeoutId;
      return (...args) => {
        window.clearTimeout(timeoutId);
        timeoutId = window.setTimeout(() => fn(...args), delay);
      };
    };

    input.addEventListener('input', debounce(applyFilter, 120));

    const clearButton = document.querySelector('.users-search .clear');
    if (clearButton) {
      clearButton.addEventListener('click', () => {
        input.value = '';
        applyFilter();
        input.focus();
      });
    }

    const params = new URLSearchParams(window.location.search);
    const presetQuery = params.get('q');
    if (presetQuery) {
      input.value = presetQuery;
      applyFilter();
    }
  }

  const blocker = document.getElementById('removeBlocker');
  const cancelButton = document.querySelector('.js-cancel-remove');
  const confirmButton = document.querySelector('.js-confirm-remove');
  let targetForm = null;

  document.querySelectorAll('.js-remove-user').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      const userId = button.dataset.userId;
      targetForm = document.getElementById(`remove_${userId}`);
      if (blocker) {
        blocker.hidden = false;
      }
    });
  });

  if (cancelButton) {
    cancelButton.addEventListener('click', () => {
      if (blocker) {
        blocker.hidden = true;
      }
      targetForm = null;
    });
  }

  if (confirmButton) {
    confirmButton.addEventListener('click', () => {
      if (targetForm) {
        targetForm.submit();
      }
    });
  }
})();
