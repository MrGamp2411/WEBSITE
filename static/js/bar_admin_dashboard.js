function initBarAdminDashboard() {
  document.querySelectorAll('.bar-toggle').forEach((btn) => {
    btn.addEventListener('click', () => {
      const table = btn.nextElementSibling;
      if (table) {
        table.hidden = !table.hidden;
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', initBarAdminDashboard);
