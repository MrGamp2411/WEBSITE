(function () {
  const assignedSearch = document.getElementById('assignedBarSearch');
  const availableSearch = document.getElementById('availableBarSearch');
  const assigned = document.getElementById('assignedBars');
  const available = document.getElementById('availableBars');

  const deleteBtn = document.querySelector('.js-delete-user');
  const blocker = document.getElementById('deleteBlocker');
  const cancelBtn = document.querySelector('.js-cancel-delete');
  const confirmBtn = document.querySelector('.js-confirm-delete');
  const deleteFormId = deleteBtn ? `delete-user-${deleteBtn.dataset.userId}` : null;
  const deleteForm = deleteFormId ? document.getElementById(deleteFormId) : null;

  deleteBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    if (blocker) {
      blocker.hidden = false;
    }
  });

  cancelBtn?.addEventListener('click', () => {
    if (blocker) {
      blocker.hidden = true;
    }
  });

  confirmBtn?.addEventListener('click', () => {
    deleteForm?.submit();
  });

  const errBlocker = document.getElementById('errorBlocker');
  errBlocker?.querySelector('.js-close-error')?.addEventListener('click', () => {
    errBlocker.hidden = true;
  });

  if (!assigned || !available) {
    return;
  }

  const container = document.getElementById('barAssignments');
  const addLabel = container?.dataset.addLabel || 'Add';
  const removeLabel = container?.dataset.removeLabel || 'Remove';

  const norm = (value) =>
    (value || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();

  const debounce = (fn, ms) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(null, args), ms);
    };
  };

  const setupSearch = (input, tbody) => {
    if (!input) {
      return () => {};
    }

    const apply = () => {
      const query = norm(input.value);
      Array.from(tbody.querySelectorAll('tr')).forEach((row) => {
        const name = row.dataset.name || '';
        row.style.display = !query || norm(name).includes(query) ? '' : 'none';
      });
    };

    const form = input.closest('.bars-search');
    form?.addEventListener('submit', (event) => {
      event.preventDefault();
      input.focus();
    });

    input.addEventListener('input', debounce(apply, 120));
    form
      ?.querySelector('.clear')
      ?.addEventListener('click', () => {
        input.value = '';
        apply();
        input.focus();
      });

    return apply;
  };

  const applyAssigned = setupSearch(assignedSearch, assigned);
  const applyAvailable = setupSearch(availableSearch, available);

  const moveRow = (row, toAssigned) => {
    const checkbox = row.querySelector('input[name="bar_ids"]');
    const button = row.querySelector('button');

    if (!checkbox || !button) {
      return;
    }

    if (toAssigned) {
      checkbox.checked = true;
      button.textContent = removeLabel;
      button.classList.remove('btn-outline');
      button.classList.add('btn-danger-soft', 'js-remove-bar');
      button.classList.remove('js-add-bar');
      assigned.appendChild(row);
    } else {
      checkbox.checked = false;
      button.textContent = addLabel;
      button.classList.remove('btn-danger-soft');
      button.classList.add('btn-outline', 'js-add-bar');
      button.classList.remove('js-remove-bar');
      available.appendChild(row);
    }

    applyAssigned();
    applyAvailable();
  };

  assigned.addEventListener('click', (event) => {
    const button = event.target.closest('.js-remove-bar');
    if (!button) {
      return;
    }

    event.preventDefault();
    moveRow(button.closest('tr'), false);
  });

  available.addEventListener('click', (event) => {
    const button = event.target.closest('.js-add-bar');
    if (!button) {
      return;
    }

    event.preventDefault();
    moveRow(button.closest('tr'), true);
  });
})();
