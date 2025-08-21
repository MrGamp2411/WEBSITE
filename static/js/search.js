const SG = window.SG ?? (window.SG = {});

SG.normalize = {
  toNumber(v, fallback = null) {
    if (v == null) return fallback;
    if (typeof v === 'number' && Number.isFinite(v)) return v;
    const m = String(v).replace(',', '.').match(/-?\d+(\.\d+)?/);
    const n = m ? parseFloat(m[0]) : NaN;
    return Number.isFinite(n) ? n : fallback;
  },
  toKm(value) {
    if (typeof value === 'number') {
      return value >= 1000 ? value / 1000 : value;
    }
    return SG.normalize.toNumber(value, null);
  },
  haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const toRad = d => d * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  },
  normText(s) {
    return (s || '').toString().normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  }
};

function validateBars(bars) {
  let missingRating = 0, missingDistance = 0, missingCoords = 0;
  for (const b of bars) {
    if (SG.normalize.toNumber(b.rating, null) == null) missingRating++;
    const km = SG.normalize.toKm(b.distance_km);
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
    const rating = SG.normalize.toNumber(b.rating, null);
    let distance_km = SG.normalize.toKm(b.distance_km);
    if (distance_km == null && userLoc && Number.isFinite(b.lat) && Number.isFinite(b.lng)) {
      distance_km = SG.normalize.haversineKm(userLoc.lat, userLoc.lng, b.lat, b.lng);
    }
    return {
      ...b,
      rating,
      distance_km,
      _searchKey: SG.normalize.normText(`${b.name} ${b.city ?? ''} ${b.address_short ?? ''}`)
    };
  });
}

function applyFilters(bars, state) {
  return bars
    .filter(b => state.q ? b._searchKey.includes(SG.normalize.normText(state.q)) : true)
    .filter(b => state.max_km == null ? true : (b.distance_km == null ? false : b.distance_km <= Number(state.max_km)))
    .filter(b => state.min_rating == null ? true : (b.rating == null ? false : b.rating >= Number(state.min_rating)))
    .filter(b => !state.categories?.length ? true : (b.categories || []).some(c => state.categories.includes(c)))
    .filter(b => state.open_now ? !!b.is_open : true);
}

document.addEventListener('DOMContentLoaded', async () => {
  const searchInput = document.getElementById('barSearch');
  const filterBtn = document.getElementById('filterBtn');
  const filterOverlay = document.getElementById('filterOverlay');
  const filterForm = document.getElementById('filterForm');
  const filterSearch = document.getElementById('filterSearch');
  const distanceInput = document.getElementById('filterDistance');
  const ratingInput = document.getElementById('filterRating');
  const distanceVal = document.getElementById('filterDistanceVal');
  const ratingVal = document.getElementById('filterRatingVal');
  const openCheckbox = document.getElementById('filterOpen');
  const categoryChips = document.getElementById('filterCategoryChips');
  const applyBtn = filterOverlay?.querySelector('.apply');
  const resetBtn = filterOverlay?.querySelector('.reset');
  const clearBtn = document.getElementById('clearFilters');
  const filterCount = document.getElementById('filterCount');

  const defaults = { q: '', max_km: null, min_rating: null, categories: [], open_now: false };
  let state = { ...defaults };
  let appliedState = { ...defaults };

  function readFromURL() {
    const p = new URLSearchParams(location.search);
    const s = { ...defaults };
    if (p.get('q')) s.q = p.get('q');
    if (p.get('max_km')) s.max_km = parseFloat(p.get('max_km'));
    if (p.get('min_rating')) s.min_rating = parseFloat(p.get('min_rating'));
    if (p.get('cat')) s.categories = p.get('cat').split(',').filter(Boolean);
    if (p.get('open_now') === '1') s.open_now = true;
    return s;
  }

  function writeToURL(s) {
    const p = new URLSearchParams();
    if (s.q) p.set('q', s.q);
    if (s.max_km != null) p.set('max_km', s.max_km);
    if (s.min_rating != null) p.set('min_rating', s.min_rating);
    if (s.categories.length) p.set('cat', s.categories.join(','));
    if (s.open_now) p.set('open_now', '1');
    const newUrl = `${location.pathname}?${p.toString()}`;
    history.replaceState(null, '', newUrl);
  }

  function readFromStorage() {
    const s = { ...defaults };
    const q = localStorage.getItem('sg.searchQuery');
    if (q) s.q = q;
    const prefix = 'sg.filters.';
    const mk = localStorage.getItem(prefix + 'max_km');
    if (mk) s.max_km = parseFloat(mk);
    const mr = localStorage.getItem(prefix + 'min_rating');
    if (mr) s.min_rating = parseFloat(mr);
    const cats = localStorage.getItem(prefix + 'categories');
    if (cats) s.categories = cats.split(',').filter(Boolean);
    const on = localStorage.getItem(prefix + 'open_now');
    if (on) s.open_now = on === '1';
    return s;
  }

  function writeToStorage(s) {
    localStorage.setItem('sg.searchQuery', s.q || '');
    const prefix = 'sg.filters.';
    s.max_km != null ? localStorage.setItem(prefix + 'max_km', s.max_km) : localStorage.removeItem(prefix + 'max_km');
    s.min_rating != null ? localStorage.setItem(prefix + 'min_rating', s.min_rating) : localStorage.removeItem(prefix + 'min_rating');
    s.categories.length ? localStorage.setItem(prefix + 'categories', s.categories.join(',')) : localStorage.removeItem(prefix + 'categories');
    localStorage.setItem(prefix + 'open_now', s.open_now ? '1' : '0');
  }

  function applyStateToControls(s) {
    if (searchInput) searchInput.value = s.q;
    if (filterSearch) filterSearch.value = s.q;
    if (distanceInput) {
      if (!distanceInput.disabled) {
        distanceInput.value = s.max_km ?? distanceInput.defaultValue;
        distanceVal.textContent = `${distanceInput.value} km`;
      } else {
        distanceVal.textContent = '';
      }
    }
    if (ratingInput) {
      if (!ratingInput.disabled) {
        ratingInput.value = s.min_rating ?? ratingInput.defaultValue;
        ratingVal.textContent = `≥ ${ratingInput.value}`;
      } else {
        ratingVal.textContent = '';
      }
    }
    if (categoryChips) {
      const chips = categoryChips.querySelectorAll('.chip');
      chips.forEach(chip => {
        const val = chip.dataset.value;
        if (!val && !s.categories.length) chip.classList.add('active');
        else if (s.categories.includes(val)) chip.classList.add('active');
        else chip.classList.remove('active');
      });
    }
    if (openCheckbox) openCheckbox.checked = s.open_now;
    checkChanges();
  }

  const cardEls = Array.from(document.querySelectorAll('.bar-card'));
  const rawBars = cardEls.map(el => ({
    el,
    id: el.getAttribute('href')?.split('/').pop(),
    name: el.dataset.name,
    address_short: el.dataset.address,
    city: el.dataset.city,
    rating: el.dataset.rating,
    distance_km: el.dataset.distance_km,
    lat: SG.normalize.toNumber(el.dataset.latitude, null),
    lng: SG.normalize.toNumber(el.dataset.longitude, null),
    categories: (el.dataset.categories || '').split(',').filter(Boolean),
    is_open: el.dataset.open === 'true'
  }));
  const report = validateBars(rawBars);
  let userLoc = null;
  let bars = await normalizeBars(rawBars, userLoc);

  bars.forEach(b => {
    const rEl = b.el.querySelector('.rating');
    if (rEl) {
      if (b.rating == null) rEl.hidden = true;
      else {
        rEl.hidden = false;
        const t = rEl.querySelector('.rating-text');
        if (t) t.textContent = b.rating.toFixed(1);
      }
    }
    const dEl = b.el.querySelector('.distance');
    if (dEl) {
      if (b.distance_km == null) dEl.hidden = true;
      else {
        dEl.hidden = false;
        const t = dEl.querySelector('.distance-text');
        if (t) t.textContent = `${b.distance_km.toFixed(1)} km`;
      }
    }
  });

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

  function applyState(s) {
    writeToURL(s);
    writeToStorage(s);
    const filtered = computeFilteredData(s);
    renderSections(filtered);
    updateFilterBadge(s);
  }

  function openFilters() {
    applyStateToControls(state);
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

  function currentFromControls() {
    return {
      q: (filterSearch ? filterSearch.value : searchInput.value).trim().toLowerCase(),
      max_km: distanceInput && !distanceInput.disabled ? parseInt(distanceInput.value, 10) : null,
      min_rating: ratingInput && !ratingInput.disabled ? parseFloat(ratingInput.value) : null,
      categories: Array.from(categoryChips.querySelectorAll('.chip.active')).map(c => c.dataset.value).filter(Boolean),
      open_now: openCheckbox.checked
    };
  }

  function checkChanges() {
    if (!applyBtn) return;
    const curr = currentFromControls();
    applyBtn.disabled = JSON.stringify(curr) === JSON.stringify(appliedState);
  }

  function debounce(fn, delay = 300) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), delay); };
  }

  const syncSearch = debounce(val => {
    state.q = val.toLowerCase();
    appliedState.q = state.q;
    if (filterSearch && filterSearch !== document.activeElement) filterSearch.value = val;
    if (searchInput && searchInput !== document.activeElement) searchInput.value = val;
    applyState(state);
  }, 300);

  searchInput?.addEventListener('input', e => syncSearch(e.target.value));
  filterSearch?.addEventListener('input', e => syncSearch(e.target.value));

  distanceInput?.addEventListener('input', () => { distanceVal.textContent = `${distanceInput.value} km`; checkChanges(); });
  ratingInput?.addEventListener('input', () => { ratingVal.textContent = `≥ ${ratingInput.value}`; checkChanges(); });
  openCheckbox?.addEventListener('input', checkChanges);

  categoryChips?.addEventListener('click', e => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    if (chip.dataset.value === '') {
      categoryChips.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
    } else {
      chip.classList.toggle('active');
      categoryChips.querySelector('[data-value=""]')?.classList.remove('active');
      if (!categoryChips.querySelector('.chip.active')) categoryChips.querySelector('[data-value=""]')?.classList.add('active');
    }
    checkChanges();
  });

  filterForm?.addEventListener('submit', e => {
    e.preventDefault();
    state = currentFromControls();
    appliedState = { ...state };
    applyState(state);
    closeFilters();
  });

  resetBtn?.addEventListener('click', () => {
    state = { ...defaults };
    appliedState = { ...defaults };
    applyStateToControls(state);
    applyState(state);
  });

  clearBtn?.addEventListener('click', () => {
    state = { ...defaults };
    appliedState = { ...defaults };
    applyStateToControls(state);
    applyState(state);
  });

  function countActiveFilters(s) {
    let c = 0;
    if (s.max_km != null) c++;
    if (s.min_rating != null) c++;
    if (s.categories.length) c++;
    if (s.open_now) c++;
    return c;
  }

  function updateFilterBadge(s) {
    if (!filterCount) return;
    const n = countActiveFilters(s);
    filterCount.textContent = n;
    filterCount.hidden = n === 0;
  }

  // Initial state
  state = readFromURL();
  const hasURLParams = Array.from(new URLSearchParams(location.search).keys()).length > 0;
  if (!hasURLParams) {
    const stored = readFromStorage();
    state = { ...state, ...stored };
  }
  appliedState = { ...state };
  applyStateToControls(state);
  applyState(state);
});
