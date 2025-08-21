document.addEventListener('DOMContentLoaded', function() {
  const nav = document.querySelector('.navbar');
  if (nav) {
    const onScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  const searchInput = document.getElementById('barSearch') || document.getElementById('barSearchDesktop');
  const barList = document.getElementById('barList');
  const nearestBarEl = document.getElementById('nearestBar');
  const locationInput = document.getElementById('locationInput') || document.getElementById('locationInputDesktop');
  const suggestionsBox = document.getElementById('searchSuggestions') || document.getElementById('searchSuggestionsDesktop');
  const locationSelectors = document.querySelectorAll('.location-selector');

  if (locationSelectors.length && locationInput) {
    locationSelectors.forEach(sel => {
      sel.addEventListener('click', () => {
        locationInput.value = '';
        locationInput.focus();
        locationInput.dispatchEvent(new Event('input'));
      });
    });
  }

  const locationPill = document.querySelector('.location-pill');
  if (locationPill && locationInput) {
    const updatePill = () => { locationPill.textContent = `📍 ${locationInput.value}`; };
    updatePill();
    ['input','change'].forEach(evt => locationInput.addEventListener(evt, updatePill));
    setTimeout(updatePill, 1000);
  }

  function filterBars(term) {
    if (!barList) return;
    const t = term.toLowerCase();
    barList.querySelectorAll('li').forEach(item => {
      const {name, address, city = '', state = ''} = item.dataset;
      item.style.display = (name.includes(t) || address.includes(t) || city.includes(t) || state.includes(t)) ? '' : 'none';
    });
  }

  function renderSuggestions(bars) {
    if (!suggestionsBox) return;
    if (!bars.length) {
      suggestionsBox.innerHTML = '';
      suggestionsBox.classList.remove('show');
      return;
    }
    const items = bars.map(bar => `
      <li data-bar-id="${bar.id}">
        <article class="card" itemscope itemtype="https://schema.org/BarOrPub">
          <img class="card__media" src="https://source.unsplash.com/random/400x250?bar,${bar.id}" alt="${bar.name}" itemprop="image" loading="lazy" decoding="async" width="400" height="250">
          <div class="card__body">
            <h3 class="card__title" itemprop="name">${bar.name}</h3>
            <p class="card__desc">${bar.description}</p>
            <address itemprop="address">${bar.address}, ${bar.city}, ${bar.state}</address>
            <a class="btn btn--primary" href="/bars/${bar.id}">View Menu</a>
          </div>
        </article>
      </li>
    `).join('');
    suggestionsBox.innerHTML = `<ul class="bars">${items}</ul>`;
    suggestionsBox.classList.add('show');
  }

  function fetchSuggestions(term) {
    if (!suggestionsBox) return;
    const q = term.trim();
    if (!q) {
      suggestionsBox.innerHTML = '';
      suggestionsBox.classList.remove('show');
      return;
    }
    fetch(`/api/search?q=${encodeURIComponent(q)}`)
      .then(res => res.json())
      .then(data => renderSuggestions(data.bars.slice(0,5)));
  }

  if (searchInput) {
    searchInput.addEventListener('focus', () => {
      searchInput.classList.add('expanded');
    });
    searchInput.addEventListener('input', () => {
      if (barList) filterBars(searchInput.value);
      fetchSuggestions(searchInput.value);
    });
    searchInput.addEventListener('blur', () => {
      setTimeout(() => {
        if (searchInput.value.trim() === '') {
          searchInput.classList.remove('expanded');
        }
        if (suggestionsBox) suggestionsBox.classList.remove('show');
      }, 100);
    });
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        window.location.href = `/search?q=${encodeURIComponent(searchInput.value)}`;
      }
    });
  }

  if (suggestionsBox) {
    suggestionsBox.addEventListener('click', (e) => {
      const li = e.target.closest('li[data-bar-id]');
      if (li) {
        const id = li.getAttribute('data-bar-id');
        window.location.href = `/bars/${id}`;
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

  const menuToggles = document.querySelectorAll('.js-open-menu');
  const mobileMenu = document.getElementById('mobileMenu');
  const backdrop = document.querySelector('.menu-backdrop');
  let activeToggle;
  let lastFocused;

  function openMenu(btn) {
    activeToggle = btn;
    lastFocused = document.activeElement;
    activeToggle.setAttribute('aria-expanded', 'true');
    mobileMenu.hidden = false;
    backdrop.hidden = false;
    requestAnimationFrame(() => {
      mobileMenu.classList.add('open');
      backdrop.classList.add('show');
    });
    document.body.style.overflow = 'hidden';
    const firstItem = mobileMenu.querySelector('[role="menuitem"]');
    firstItem && firstItem.focus();
  }

  function closeMenu() {
    activeToggle && activeToggle.setAttribute('aria-expanded', 'false');
    mobileMenu.classList.remove('open');
    backdrop.classList.remove('show');
    document.body.style.overflow = '';
    mobileMenu.hidden = true;
    backdrop.hidden = true;
    lastFocused && lastFocused.focus();
  }

  menuToggles.forEach(btn => {
    btn.addEventListener('click', () => {
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      expanded ? closeMenu() : openMenu(btn);
    });
  });

  backdrop?.addEventListener('click', closeMenu);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !mobileMenu.hidden) {
      closeMenu();
    }
  });

  mobileMenu?.addEventListener('click', (e) => {
    if (e.target.closest('[role="menuitem"]')) {
      closeMenu();
    }
  });

  mobileMenu?.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    const items = mobileMenu.querySelectorAll('[role="menuitem"]');
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  document.querySelector('.js-open-search')?.addEventListener('click', () => {
    const ov = document.querySelector('.search-overlay');
    ov?.classList.add('open');
    ov?.removeAttribute('hidden');
  });
  document.querySelector('.overlay-close')?.addEventListener('click', () => {
    const ov = document.querySelector('.search-overlay');
    ov?.classList.remove('open');
    ov?.setAttribute('hidden','');
  });
});
