document.addEventListener('DOMContentLoaded', function() {
  const searchInput = document.getElementById('barSearch');
  const barList = document.getElementById('barList');
  const nearestBarEl = document.getElementById('nearestBar');
  const locationInput = document.getElementById('locationInput');
  // Elements used solely for search suggestions have been removed

  function filterBars(term) {
    if (!barList) return;
    const t = term.toLowerCase();
    barList.querySelectorAll('li').forEach(item => {
      const {name, address, city = '', state = ''} = item.dataset;
      item.style.display = (name.includes(t) || address.includes(t) || city.includes(t) || state.includes(t)) ? '' : 'none';
    });
  }

  // Suggestion dropdown and preview overlay have been removed

  if (searchInput) {
    searchInput.addEventListener('focus', () => {
      searchInput.classList.add('expanded');
    });
    searchInput.addEventListener('input', () => {
      if (barList) filterBars(searchInput.value);
    });
    searchInput.addEventListener('blur', () => {
      if (searchInput.value.trim() === '') {
        searchInput.classList.remove('expanded');
      }
    });
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        window.location.href = `/search?q=${encodeURIComponent(searchInput.value)}`;
      }
    });
  }

  const allBarItems = document.querySelectorAll('ul.bars li');

  function updateDistances(uLat, uLon) {
    allBarItems.forEach(item => {
      const bLat = parseFloat(item.dataset.latitude);
      const bLon = parseFloat(item.dataset.longitude);
      if (!isFinite(bLat) || !isFinite(bLon)) return;
      const dist = haversine(uLat, uLon, bLat, bLon);
      item.dataset.distance = dist;
      const distEl = item.querySelector('.distance');
      if (distEl) {
        const link = document.createElement('a');
        link.textContent = `📍 ${dist.toFixed(1)} km away`;
        link.href = '#';
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const isApple = /iPad|iPhone|Mac/i.test(navigator.platform);
          const url = isApple
            ? `https://maps.apple.com/?daddr=${bLat},${bLon}`
            : `https://www.google.com/maps/dir/?api=1&destination=${bLat},${bLon}`;
          window.open(url, '_blank');
        });
        distEl.innerHTML = '';
        distEl.appendChild(link);
      }
    });

    if (barList) {
      const items = Array.from(barList.querySelectorAll('li')).filter(li => li.style.display !== 'none');
      items.sort((a, b) => parseFloat(a.dataset.distance) - parseFloat(b.dataset.distance));
      items.forEach(item => barList.appendChild(item));
      if (nearestBarEl && items.length) {
        const nearest = items[0];
        const name = nearest.querySelector('.card__title').textContent;
        nearestBarEl.textContent = `Nearest bar: ${name} (${parseFloat(nearest.dataset.distance).toFixed(1)} km)`;
      }
    }
  }

  function reverseGeocode(lat, lon) {
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`)
      .then(res => res.json())
      .then(data => {
        if (!locationInput) return;
        if (data.address) {
          const {city, town, village, postcode} = data.address;
          const place = city || town || village;
          if (place) {
            locationInput.value = postcode ? `${place} ${postcode}` : place;
            return;
          }
        }
        locationInput.value = data.display_name || `${lat.toFixed(3)}, ${lon.toFixed(3)}`;
      })
      .catch(() => {
        if (locationInput) locationInput.value = `${lat.toFixed(3)}, ${lon.toFixed(3)}`;
      });
  }

  function setLocation(lat, lon, label) {
    updateDistances(lat, lon);
    if (locationInput) {
      locationInput.value = label || `${lat.toFixed(3)}, ${lon.toFixed(3)}`;
    }
    reverseGeocode(lat, lon);
  }

  if (allBarItems.length) {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(pos => {
        const {latitude, longitude} = pos.coords;
        setLocation(latitude, longitude);
      });
    }

    function geocodeAndSet(city) {
      fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(city)}`)
        .then(res => res.json())
        .then(data => {
          if (data && data.length) {
            const {lat, lon} = data[0];
            setLocation(parseFloat(lat), parseFloat(lon), city);
          }
        });
    }

    if (locationInput) {
      locationInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const city = locationInput.value.trim();
          if (city) geocodeAndSet(city);
        }
      });
    }
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
