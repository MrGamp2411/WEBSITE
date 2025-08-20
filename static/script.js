document.addEventListener('DOMContentLoaded', function() {
  const searchInput = document.getElementById('barSearch');
  const barList = document.getElementById('barList');
  if (searchInput && barList) {
    searchInput.addEventListener('keyup', function() {
      const term = this.value.toLowerCase();
      barList.querySelectorAll('li').forEach(item => {
        const {name, address, city = '', state = ''} = item.dataset;
        item.style.display = (name.includes(term) || address.includes(term) || city.includes(term) || state.includes(term)) ? '' : 'none';
      });
    });
  }

  if (barList && navigator.geolocation) {
    const nearestBarEl = document.getElementById('nearestBar');
    navigator.geolocation.getCurrentPosition(pos => {
      const {latitude: uLat, longitude: uLon} = pos.coords;
      const items = Array.from(barList.querySelectorAll('li'));
      items.forEach(item => {
        const bLat = parseFloat(item.dataset.latitude);
        const bLon = parseFloat(item.dataset.longitude);
        const dist = haversine(uLat, uLon, bLat, bLon);
        item.dataset.distance = dist;
      });
      items.sort((a, b) => a.dataset.distance - b.dataset.distance);
      items.forEach(item => barList.appendChild(item));
      if (nearestBarEl && items.length) {
        const nearest = items[0];
        const name = nearest.querySelector('.card__title').textContent;
        nearestBarEl.textContent = `Nearest bar: ${name} (${Number(nearest.dataset.distance).toFixed(1)} km)`;
      }
    });
  }

  function haversine(lat1, lon1, lat2, lon2) {
    const toRad = deg => deg * Math.PI / 180;
    const R = 6371;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  const toggle = document.getElementById('themeToggle');
  if (toggle) {
    const applyTheme = (mode) => {
      document.body.classList.toggle('dark-mode', mode === 'dark');
      toggle.textContent = mode === 'dark' ? '☀️' : '🌙';
      toggle.setAttribute('aria-label', mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    };
    toggle.addEventListener('click', () => {
      const mode = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
      applyTheme(mode);
      localStorage.setItem('theme', mode);
    });
    const stored = localStorage.getItem('theme') || 'light';
    applyTheme(stored);
  }

  const menuToggle = document.getElementById('menuToggle');
  const mobileMenu = document.getElementById('mobileMenu');
  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener('click', () => {
      const expanded = menuToggle.getAttribute('aria-expanded') === 'true';
      menuToggle.setAttribute('aria-expanded', String(!expanded));
      mobileMenu.hidden = expanded;
      mobileMenu.classList.toggle('open', !expanded);
    });
  }
});
