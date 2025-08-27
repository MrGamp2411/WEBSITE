function toNumber(v) {
  if (v == null) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  const m = String(v).replace(',', '.').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
}

function toKm(v) {
  if (v == null) return null;
  if (typeof v === 'number') return v >= 1000 ? v / 1000 : v;
  const n = toNumber(v);
  return n;
}

const norm = s => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const toRad = d => d * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function renderMeta(el, bar) {
  const rating = toNumber(bar.rating);
  const km = toKm(bar.distance_km);
  const rEl = el.querySelector('.bar-rating');
  const dEl = el.querySelector('.bar-distance');
  if (rEl) {
    if (rating != null) {
      rEl.innerHTML = '<i class="bi bi-star-fill" aria-hidden="true"></i> <span class="rating-value">' + rating.toFixed(1) + '</span>';
      rEl.hidden = false;
      rEl.dataset.hasRating = 'true';
    } else {
      rEl.hidden = true;
      rEl.dataset.hasRating = 'false';
    }
  }
  if (dEl) {
    if (km != null) {
      dEl.innerHTML = '<i class="bi bi-geo-alt-fill" aria-hidden="true"></i> <span class="distance-value">' + km.toFixed(1) + ' km</span>';
      dEl.hidden = false;
      dEl.dataset.hasDistance = 'true';
    } else {
      dEl.hidden = true;
      dEl.dataset.hasDistance = 'false';
    }
  }
}

function validateBars(bars) {
  let missingRating = 0, missingDistance = 0, missingCoords = 0;
  for (const b of bars) {
    if (toNumber(b.rating) == null) missingRating++;
    const km = toKm(b.distance_km);
    if (km == null) missingDistance++;
    if (!(Number.isFinite(b.lat) && Number.isFinite(b.lng))) missingCoords++;
  }
  console.table([
    { metric: 'total', value: bars.length },
    { metric: 'missing rating', value: missingRating },
    { metric: 'missing distance_km', value: missingDistance },
    { metric: 'missing lat/lng', value: missingCoords }
  ]);
  return { total: bars.length, missingRating, missingDistance, missingCoords };
}

async function normalizeBars(bars, userLoc) {
  return bars.map(b => {
    const rating = toNumber(b.rating);
    let distance_km = toKm(b.distance_km);
    if (distance_km == null && userLoc && Number.isFinite(b.lat) && Number.isFinite(b.lng)) {
      distance_km = haversineKm(userLoc.lat, userLoc.lng, b.lat, b.lng);
    }
    return {
      ...b,
      rating,
      distance_km,
      _searchKey: norm(`${b.name} ${b.city ?? ''}`)
    };
  });
}

function applyFilters(bars, state) {
  return bars
    .filter(b => state.q ? b._searchKey.includes(norm(state.q)) : true)
    .filter(b => state.active.max_km ? (b.distance_km == null ? false : b.distance_km <= Number(state.max_km)) : true)
    .filter(b => state.active.min_rating ? (b.rating == null ? false : b.rating >= Number(state.min_rating)) : true)
    .filter(b => state.active.categories ? (b.categories || []).some(c => state.categories.includes(c)) : true)
    .filter(b => state.open_now ? (!!b.is_open || b.is_recent) : true);
}

document.addEventListener('DOMContentLoaded', async () => {
  const searchInput = document.getElementById('barSearch');
  const filterBtn = document.getElementById('filterBtn');
  const filterOverlay = document.getElementById('filterOverlay');
  const filterForm = document.getElementById('filterForm');
  const distanceInput = document.getElementById('filterDistance');
  const ratingInput = document.getElementById('filterRating');
  const distanceToggle = document.getElementById('filterDistanceToggle');
  const ratingToggle = document.getElementById('filterRatingToggle');
  const distanceVal = document.getElementById('filterDistanceVal');
  const ratingVal = document.getElementById('filterRatingVal');
  const distanceAnnounce = document.getElementById('filterDistanceAnnounce');
  const ratingAnnounce = document.getElementById('filterRatingAnnounce');
  const categoryChips = document.getElementById('filterCategoryChips');
  const categoryVal = document.getElementById('filterCategoryVal');
  const openCheckbox = document.getElementById('filterOpen');
  const openVal = document.getElementById('filterOpenVal');
  const applyBtn = filterOverlay?.querySelector('.apply');
  const resetBtn = filterOverlay?.querySelector('.reset');
  const clearBtn = document.getElementById('clearFilters');
  const filterCount = document.getElementById('filterCount');

  const defaults = {
    q: '',
    max_km: null,
    min_rating: null,
    categories: [],
    open_now: true,
    active: { max_km: false, min_rating: false, categories: false }
  };
  let state = JSON.parse(JSON.stringify(defaults));
  let appliedState = JSON.parse(JSON.stringify(defaults));

  const cardEls = Array.from(document.querySelectorAll('.bar-card'));
  const rawBars = cardEls.map(el => ({
    el,
    id: el.getAttribute('href')?.split('/').pop(),
    name: el.dataset.name,
    address_short: el.dataset.address,
    city: el.dataset.city,
    rating: el.dataset.rating,
    distance_km: el.dataset.distance_km,
    lat: toNumber(el.dataset.latitude),
    lng: toNumber(el.dataset.longitude),
    categories: (el.dataset.categories || '').split(',').filter(Boolean),
    is_open: el.dataset.open === 'true',
    is_recent: el.closest('[data-section="recent"]') !== null
  }));
  validateBars(rawBars);
    let userLoc = null;
    let bars = await normalizeBars(rawBars, userLoc);

    bars.forEach(b => renderMeta(b.el, b));

    const topSection = document.querySelector('.bar-section[data-section="top"]');

    async function filterTopByDistance(pos) {
      if (!topSection) return;
      if (pos) {
        userLoc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        bars = await normalizeBars(rawBars, userLoc);
        bars.forEach(b => renderMeta(b.el, b));
      }
      const topBars = bars.filter(b => b.el.closest('[data-section="top"]'));
      topBars.forEach(b => {
        if (b.distance_km != null && b.distance_km > 5) {
          b.el.remove();
        }
      });
      if (!topSection.querySelector('.bar-card')) {
        const msg = document.createElement('p');
        msg.textContent = 'Non ci sono bar nelle tue vicinanze.';
        topSection.appendChild(msg);
      }
      bars = bars.filter(b => document.body.contains(b.el));
    }

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(filterTopByDistance, () => filterTopByDistance());
    } else {
      filterTopByDistance();
    }

    if (distanceInput && bars.every(b => b.distance_km == null)) {
      distanceInput.disabled = true;
      const msg = document.createElement('p');
      msg.className = 'help';
    msg.textContent = 'Nessuna distanza disponibile per questi risultati.';
    distanceInput.closest('.group')?.appendChild(msg);
  }
  if (ratingInput && bars.every(b => b.rating == null)) {
    ratingInput.disabled = true;
    const msg = document.createElement('p');
    msg.className = 'help';
    msg.textContent = 'Nessuna valutazione disponibile per questi risultati.';
    ratingInput.closest('.group')?.appendChild(msg);
  }

  const allCards = cardEls;

  function computeFilteredData(s) {
    const filtered = applyFilters(bars, s);
    return filtered.map(b => b.el);
  }

  function renderSections(filtered) {
    allCards.forEach(c => (c.style.display = 'none'));
    filtered.forEach(c => (c.style.display = ''));
    document.querySelectorAll('.bar-section').forEach(section => {
      const visible = section.querySelectorAll('.bar-card:not([style*="display: none"])').length;
      section.style.display = visible ? '' : 'none';
    });
    const empty = document.querySelector('.empty-state');
    if (empty) empty.style.display = filtered.length ? 'none' : '';
  }

  function writeToURL(s) {
    const p = new URLSearchParams();
    if (s.q) p.set('q', s.q);
    if (s.active.max_km) p.set('max_km', s.max_km);
    if (s.active.min_rating) p.set('min_rating', s.min_rating);
    if (s.active.categories) p.set('cat', s.categories.join(','));
    if (!s.open_now) p.set('open_now', '0');
    const newUrl = `${location.pathname}?${p.toString()}`;
    history.replaceState(null, '', newUrl);
  }

  function writeToStorage(s) {
    localStorage.setItem('sg.searchQuery', s.q || '');
    const prefix = 'sg.filters.';
    if (s.active.max_km) {
      localStorage.setItem(prefix + 'max_km', s.max_km);
      localStorage.setItem(prefix + 'active.max_km', '1');
    } else {
      localStorage.removeItem(prefix + 'max_km');
      localStorage.removeItem(prefix + 'active.max_km');
    }
    if (s.active.min_rating) {
      localStorage.setItem(prefix + 'min_rating', s.min_rating);
      localStorage.setItem(prefix + 'active.min_rating', '1');
    } else {
      localStorage.removeItem(prefix + 'min_rating');
      localStorage.removeItem(prefix + 'active.min_rating');
    }
    if (s.active.categories) {
      localStorage.setItem(prefix + 'categories', s.categories.join(','));
      localStorage.setItem(prefix + 'active.categories', '1');
    } else {
      localStorage.removeItem(prefix + 'categories');
      localStorage.removeItem(prefix + 'active.categories');
    }
    if (!s.open_now) {
      localStorage.setItem(prefix + 'open_now', '0');
    } else {
      localStorage.removeItem(prefix + 'open_now');
    }
  }

  function readFromURL() {
    const p = new URLSearchParams(location.search);
    const s = JSON.parse(JSON.stringify(defaults));
    if (p.get('q')) s.q = p.get('q');
    if (p.get('max_km')) { s.max_km = parseFloat(p.get('max_km')); s.active.max_km = true; }
    if (p.get('min_rating')) { s.min_rating = parseFloat(p.get('min_rating')); s.active.min_rating = true; }
    if (p.get('cat')) { s.categories = p.get('cat').split(',').filter(Boolean); s.active.categories = true; }
    if (p.has('open_now')) { s.open_now = p.get('open_now') === '1'; }
    return s;
  }

  function readFromStorage() {
    const s = JSON.parse(JSON.stringify(defaults));
    const q = localStorage.getItem('sg.searchQuery');
    if (q) s.q = q;
    const prefix = 'sg.filters.';
    if (localStorage.getItem(prefix + 'active.max_km') === '1') {
      const mk = localStorage.getItem(prefix + 'max_km');
      if (mk) { s.max_km = parseFloat(mk); s.active.max_km = true; }
    }
    if (localStorage.getItem(prefix + 'active.min_rating') === '1') {
      const mr = localStorage.getItem(prefix + 'min_rating');
      if (mr) { s.min_rating = parseFloat(mr); s.active.min_rating = true; }
    }
    if (localStorage.getItem(prefix + 'active.categories') === '1') {
      const cats = localStorage.getItem(prefix + 'categories');
      if (cats) { s.categories = cats.split(',').filter(Boolean); s.active.categories = true; }
    }
    const on = localStorage.getItem(prefix + 'open_now');
    if (on !== null) { s.open_now = on === '1'; }
    return s;
  }

  function updateControls() {
    if (searchInput) searchInput.value = state.q;
    if (distanceInput) {
      const group = distanceInput.closest('.group');
      distanceToggle && (distanceToggle.checked = state.active.max_km);
      distanceInput.value = state.max_km ?? distanceInput.defaultValue;
      if (state.active.max_km && state.max_km != null && !distanceInput.disabled) {
        distanceVal.textContent = `${state.max_km} km`;
        distanceVal.hidden = false;
        group.dataset.active = 'true';
      } else {
        distanceVal.textContent = '';
        distanceVal.hidden = true;
        group.dataset.active = 'false';
      }
      distanceInput.setAttribute('aria-valuenow', distanceInput.value);
      if (distanceAnnounce) distanceAnnounce.textContent = state.active.max_km ? `${state.max_km} km` : '';
    }
    if (ratingInput) {
      const group = ratingInput.closest('.group');
      ratingToggle && (ratingToggle.checked = state.active.min_rating);
      ratingInput.value = state.min_rating ?? ratingInput.defaultValue;
      if (state.active.min_rating && state.min_rating != null && !ratingInput.disabled) {
        ratingVal.textContent = `≥ ${state.min_rating.toFixed(1)}`;
        ratingVal.hidden = false;
        group.dataset.active = 'true';
      } else {
        ratingVal.textContent = '';
        ratingVal.hidden = true;
        group.dataset.active = 'false';
      }
      ratingInput.setAttribute('aria-valuenow', ratingInput.value);
      if (ratingAnnounce) ratingAnnounce.textContent = state.active.min_rating ? `${state.min_rating.toFixed(1)}` : '';
    }
    if (categoryChips) {
      const group = categoryChips.closest('.group');
      const chips = categoryChips.querySelectorAll('.chip');
      chips.forEach(chip => {
        const val = chip.dataset.value;
        chip.classList.toggle('active', state.active.categories && state.categories.includes(val));
      });
      if (state.active.categories) {
        let text = '';
        if (state.categories.length === 1) {
          const chipEl = categoryChips.querySelector(`.chip[data-value="${state.categories[0]}"]`);
          text = chipEl ? chipEl.textContent.trim() : state.categories[0];
        } else if (state.categories.length > 1) {
          const chipEl = categoryChips.querySelector(`.chip[data-value="${state.categories[0]}"]`);
          const label = chipEl ? chipEl.textContent.trim() : state.categories[0];
          text = `${label} +${state.categories.length - 1}`;
        }
        categoryVal.textContent = text;
        categoryVal.hidden = false;
        group.dataset.active = 'true';
      } else {
        categoryVal.textContent = '';
        categoryVal.hidden = true;
        group.dataset.active = 'false';
      }
    }
    if (openCheckbox) {
      const group = openCheckbox.closest('.group');
      openCheckbox.checked = state.open_now;
      openVal.textContent = state.open_now ? 'Sì' : 'No';
      openVal.hidden = !state.open_now;
      group.dataset.active = state.open_now ? 'true' : 'false';
    }
    const activeCount = Object.values(state.active).filter(Boolean).length;
    const openChanged = state.open_now !== defaults.open_now;
    applyBtn && (applyBtn.disabled = activeCount === 0 && !openChanged);
  }

  function updateFilterBadge(s) {
    if (!filterCount) return;
    const n = Object.values(s.active).filter(Boolean).length;
    if (n > 0) {
      filterCount.textContent = n;
      filterCount.hidden = false;
    } else {
      filterCount.textContent = '';
      filterCount.hidden = true;
    }
  }

  function applyState(s) {
    writeToURL(s);
    writeToStorage(s);
    const filtered = computeFilteredData(s);
    renderSections(filtered);
    updateFilterBadge(s);
  }

  function openFilters() {
    state = JSON.parse(JSON.stringify(appliedState));
    updateControls();
    filterOverlay.hidden = false;
    requestAnimationFrame(() => filterOverlay.classList.add('show'));
    document.body.style.overflow = 'hidden';
    const first = filterOverlay.querySelector('input,button');
    first && first.focus();
  }
  function closeFilters() {
    filterOverlay.classList.remove('show');
    document.body.style.overflow = '';
    filterOverlay.hidden = true;
    filterBtn && filterBtn.focus();
  }

  filterBtn?.addEventListener('click', openFilters);
  filterOverlay?.addEventListener('click', e => { if (e.target === filterOverlay) closeFilters(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !filterOverlay.hidden) closeFilters(); });
  filterOverlay?.addEventListener('keydown', e => {
    if (e.key !== 'Tab') return;
    const focusable = filterOverlay.querySelectorAll('input,button');
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  const debounce = (fn, delay = 300) => { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), delay); }; };

  const syncSearch = debounce(val => {
    state.q = val;
    appliedState.q = val;
    applyState(appliedState);
  }, 300);

  searchInput?.addEventListener('input', e => syncSearch(e.target.value));

  distanceToggle?.addEventListener('change', e => {
    state.active.max_km = e.target.checked;
    state.max_km = e.target.checked ? +distanceInput.value : null;
    updateControls();
  });

  ratingToggle?.addEventListener('change', e => {
    state.active.min_rating = e.target.checked;
    state.min_rating = e.target.checked ? +ratingInput.value : null;
    updateControls();
  });

  distanceInput?.addEventListener('input', e => {
    state.max_km = +e.target.value;
    distanceInput.setAttribute('aria-valuenow', e.target.value);
    if (distanceAnnounce) distanceAnnounce.textContent = `${e.target.value} km`;
    updateControls();
  });

  ratingInput?.addEventListener('input', e => {
    state.min_rating = +e.target.value;
    ratingInput.setAttribute('aria-valuenow', e.target.value);
    if (ratingAnnounce) ratingAnnounce.textContent = `${parseFloat(e.target.value).toFixed(1)}`;
    updateControls();
  });

  openCheckbox?.addEventListener('change', e => {
    state.open_now = e.target.checked;
    updateControls();
  });

  categoryChips?.addEventListener('click', e => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    const val = chip.dataset.value;
    if (!val) {
      state.categories = [];
      state.active.categories = false;
    } else {
      if (!state.active.categories) {
        state.active.categories = true;
        state.categories = [val];
      } else {
        if (state.categories.includes(val)) {
          state.categories = state.categories.filter(c => c !== val);
          if (state.categories.length === 0) state.active.categories = false;
        } else {
          state.categories.push(val);
        }
      }
    }
    updateControls();
  });

  function rangeKeyHandler(e) {
    const input = e.target;
    const step = Number(input.step) || 1;
    const min = Number(input.min) || 0;
    const max = Number(input.max) || 100;
    let val = Number(input.value);
    switch(e.key){
      case 'ArrowUp':
      case 'ArrowRight':
        val = Math.min(val + step, max); break;
      case 'ArrowDown':
      case 'ArrowLeft':
        val = Math.max(val - step, min); break;
      case 'PageUp':
        val = Math.min(val + step*5, max); break;
      case 'PageDown':
        val = Math.max(val - step*5, min); break;
      case 'Home':
        val = min; break;
      case 'End':
        val = max; break;
      default:
        return;
    }
    e.preventDefault();
    input.value = val;
    input.dispatchEvent(new Event('input', {bubbles:true}));
  }

  distanceInput?.addEventListener('keydown', rangeKeyHandler);
  ratingInput?.addEventListener('keydown', rangeKeyHandler);

  filterForm?.addEventListener('submit', e => {
    e.preventDefault();
    appliedState = JSON.parse(JSON.stringify(state));
    applyState(appliedState);
    closeFilters();
  });

  resetBtn?.addEventListener('click', () => {
    state = JSON.parse(JSON.stringify(defaults));
    appliedState = JSON.parse(JSON.stringify(defaults));
    updateControls();
    applyState(appliedState);
  });

  clearBtn?.addEventListener('click', () => {
    state = JSON.parse(JSON.stringify(defaults));
    appliedState = JSON.parse(JSON.stringify(defaults));
    updateControls();
    applyState(appliedState);
  });

  // Initial state
  state = readFromURL();
  const hasParams = Array.from(new URLSearchParams(location.search).keys()).length > 0;
  if (!hasParams) {
    state = readFromStorage();
  }
  appliedState = JSON.parse(JSON.stringify(state));
  updateControls();
  applyState(appliedState);
});

