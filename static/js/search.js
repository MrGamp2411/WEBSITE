document.addEventListener('DOMContentLoaded', () => {
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
      distanceInput.value = s.max_km ?? distanceInput.defaultValue;
      distanceVal.textContent = `${distanceInput.value} km`;
    }
    if (ratingInput) {
      ratingInput.value = s.min_rating ?? ratingInput.defaultValue;
      ratingVal.textContent = `≥ ${ratingInput.value}`;
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

  const allCards = Array.from(document.querySelectorAll('.bar-card'));

  function computeFilteredData(cards, s) {
    return cards.filter(card => {
      const name = (card.dataset.name || '').toLowerCase();
      const city = (card.dataset.city || '').toLowerCase();
      if (s.q && !name.includes(s.q) && !city.includes(s.q)) return false;
      const dist = parseFloat(card.dataset.distance_km || card.dataset.distance || '');
      if (s.max_km != null && (!isFinite(dist) || dist > s.max_km)) return false;
      const rating = parseFloat(card.dataset.rating || '');
      if (s.min_rating != null && (!isFinite(rating) || rating < s.min_rating)) return false;
      const cats = (card.dataset.categories || '').split(',').filter(Boolean);
      if (s.categories.length && !s.categories.some(c => cats.includes(c))) return false;
      const open = card.dataset.open === 'true';
      if (s.open_now && !open) return false;
      return true;
    });
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
    renderSections(computeFilteredData(allCards, s));
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
      max_km: parseInt(distanceInput.value, 10),
      min_rating: parseFloat(ratingInput.value),
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
