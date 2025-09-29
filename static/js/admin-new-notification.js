(function () {
  const form = document.getElementById('notificationForm');
  if (!form) {
    return;
  }

  const target = document.getElementById('target');
  const userSection = document.getElementById('userSection');
  const barSection = document.getElementById('barSection');
  const userInput = document.getElementById('user_id');
  const barInput = document.getElementById('bar_id');

  const texts = {
    selectUser: form.dataset.selectUser || 'Please select a user.',
    selectBar: form.dataset.selectBar || 'Please select a bar.',
    select: form.dataset.selectLabel || 'Select',
    selected: form.dataset.selectedLabel || 'Selected',
  };

  const updateTarget = () => {
    const value = target.value;
    const isUser = value === 'user';
    const isBar = value === 'bar';

    if (userSection) {
      userSection.hidden = !isUser;
    }

    if (barSection) {
      barSection.hidden = !isBar;
    }

    if (userInput) {
      userInput.disabled = !isUser;
      if (!isUser) {
        userInput.value = '';
      }
    }

    if (barInput) {
      barInput.disabled = !isBar;
      if (!isBar) {
        barInput.value = '';
      }
    }
  };

  target?.addEventListener('change', updateTarget);
  updateTarget();

  form.addEventListener('submit', (event) => {
    const value = target.value;
    const needsUser = value === 'user' && !userInput?.value;
    const needsBar = value === 'bar' && !barInput?.value;

    if (needsUser || needsBar) {
      event.preventDefault();
      alert(needsUser ? texts.selectUser : texts.selectBar);
    }
  });

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
    if (!input || !tbody) {
      return;
    }

    const apply = () => {
      const query = norm(input.value);
      Array.from(tbody.querySelectorAll('tr')).forEach((row) => {
        const name = row.dataset.name || '';
        row.style.display = !query || norm(name).includes(query) ? '' : 'none';
      });
    };

    input.addEventListener('input', debounce(apply, 120));
    input.closest('.users-search, .bars-search')
      ?.querySelector('.clear')
      ?.addEventListener('click', () => {
        input.value = '';
        apply();
        input.focus();
      });
  };

  setupSearch(document.getElementById('userSearch'), document.getElementById('userRows'));
  setupSearch(document.getElementById('barSearch'), document.getElementById('barRows'));

  document.getElementById('userRows')?.addEventListener('click', (event) => {
    const button = event.target.closest('.js-pick-user');
    if (!button) {
      return;
    }

    event.preventDefault();
    if (userInput) {
      userInput.value = button.dataset.userId || '';
    }
    document
      .querySelectorAll('.js-pick-user')
      .forEach((node) => {
        node.textContent = texts.select;
      });
    button.textContent = texts.selected;
  });

  document.getElementById('barRows')?.addEventListener('click', (event) => {
    const button = event.target.closest('.js-pick-bar');
    if (!button) {
      return;
    }

    event.preventDefault();
    if (barInput) {
      barInput.value = button.dataset.barId || '';
    }
    document
      .querySelectorAll('.js-pick-bar')
      .forEach((node) => {
        node.textContent = texts.select;
      });
    button.textContent = texts.selected;
  });
})();
