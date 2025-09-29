(function () {
  const dataEl = document.getElementById('adminAnalyticsData');
  if (!dataEl) {
    return;
  }

  let payload;
  try {
    payload = JSON.parse(dataEl.textContent);
  } catch (error) {
    console.error('Failed to parse analytics data', error);
    return;
  }

  const {
    dailyLabels = [],
    dailyGmv = [],
    dailyOrders = [],
    chartLabels = {},
    revenueBars = [],
    hourlyLabels = [],
    hourlyOrders = []
  } = payload || {};

  if (typeof Chart === 'undefined') {
    return;
  }

  const gmvCanvas = document.getElementById('gmvChart');
  if (gmvCanvas) {
    new Chart(gmvCanvas, {
      type: 'line',
      data: {
        labels: dailyLabels,
        datasets: [
          { label: chartLabels.gmv, data: dailyGmv, borderColor: '#0d6efd', fill: false },
          { label: chartLabels.orders, data: dailyOrders, borderColor: '#6c757d', fill: false, yAxisID: 'y1' }
        ]
      },
      options: {
        scales: {
          y: { beginAtZero: true },
          y1: { beginAtZero: true, position: 'right' }
        }
      }
    });
  }

  const revenueCanvas = document.getElementById('revenueChart');
  if (revenueCanvas && Array.isArray(revenueBars) && revenueBars.length) {
    const revLabels = revenueBars.map((row) => row.bar);
    const revGmv = revenueBars.map((row) => row.gmv);
    const revCommission = revenueBars.map((row) => row.commission);
    const revNet = revenueBars.map((row) => row.net);

    new Chart(revenueCanvas, {
      type: 'bar',
      data: {
        labels: revLabels,
        datasets: [
          { label: chartLabels.gmv, data: revGmv, backgroundColor: '#0d6efd' },
          { label: chartLabels.commission, data: revCommission, backgroundColor: '#dc3545' },
          { label: chartLabels.net, data: revNet, backgroundColor: '#198754' }
        ]
      },
      options: {
        scales: {
          y: { beginAtZero: true }
        }
      }
    });
  }

  const ordersCanvas = document.getElementById('ordersChart');
  if (ordersCanvas) {
    new Chart(ordersCanvas, {
      type: 'line',
      data: {
        labels: hourlyLabels,
        datasets: [
          { label: chartLabels.orders_per_hour, data: hourlyOrders, borderColor: '#0d6efd', fill: false }
        ]
      },
      options: {
        scales: {
          y: { beginAtZero: true }
        }
      }
    });
  }

  document.querySelectorAll('.tab-nav a').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const targetId = link.dataset.tab;
      if (!targetId) {
        return;
      }

      document.querySelectorAll('.tab-nav a').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach((section) => section.classList.remove('active'));

      link.classList.add('active');
      const targetSection = document.getElementById(targetId);
      if (targetSection) {
        targetSection.classList.add('active');
      }
    });
  });
})();
