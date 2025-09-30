document.addEventListener('DOMContentLoaded', () => {
  const fieldFilter = document.querySelector('[data-field-filter]');
  if (!fieldFilter) {
    return;
  }

  const rows = Array.from(document.querySelectorAll('[data-update-row]'));
  const emptyRow = document.querySelector('[data-no-results]');

  const applyFilter = () => {
    const { value } = fieldFilter;
    let visibleCount = 0;

    rows.forEach(row => {
      const matches = value === '' || row.dataset.field === value;
      row.hidden = !matches;
      if (matches) {
        visibleCount += 1;
      }
    });

    if (emptyRow) {
      emptyRow.hidden = visibleCount !== 0;
    }
  };

  fieldFilter.addEventListener('change', applyFilter);
  applyFilter();
});
