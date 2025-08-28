function toNumber(v) {
  if (v == null) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  const m = String(v).replace(',', '.').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
}

const norm = s => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function debounce(fn, delay){
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), delay);
  };
}

function throttle(fn, limit){
  let waiting = false;
  return (...args) => {
    if (!waiting) {
      fn.apply(this, args);
      waiting = true;
      setTimeout(() => waiting = false, limit);
    }
  };
}

function renderMeta(el, data) {
  const rating = toNumber(data.rating);
  const km = toNumber(data.distance_km);
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

function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const toRad = d => d * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

document.addEventListener('DOMContentLoaded', () => {
  const list = document.getElementById('allBarList');
  if (!list) return;
  const cards = Array.from(list.querySelectorAll('.bar-card'));

  const nameInput = document.getElementById('searchName');
  const cityInput = document.getElementById('searchCity');
  const distInput = document.getElementById('filterDistance');
  const ratingInput = document.getElementById('filterRating');
  const ratingStars = document.getElementById('ratingStars');
  const ratingValue = document.getElementById('ratingValue');
  const openCheck = document.getElementById('filterOpen');
  const closedCheck = document.getElementById('filterClosed');
  const chipsContainer = document.getElementById('categoryChips');
  const activeChips = document.getElementById('activeFilterChips');
  const filterBadge = document.getElementById('filterCount');
  const distanceValue = document.getElementById('distanceValue');
  const activeCategories = new Set();

  if (distInput) {
    distInput.value = distInput.max || '30';
    distanceValue.textContent = distInput.value + ' km';
  }

  let setRating = val => {
    if (ratingInput) {
      ratingInput.value = val || '';
      ratingStars?.setAttribute('aria-valuenow', val || 0);
      updateRatingDisplay();
    }
  };
  let updateRatingDisplay = () => {
    if (!ratingStars) return;
    const val = toNumber(ratingInput?.value);
    ratingValue.textContent = val ? '≥ ' + val.toFixed(1) : '';
    const r = val || 0;
    Array.from(ratingStars.children).forEach((s, i) => {
      const idx = i + 1;
      s.className = r >= idx ? 'bi bi-star-fill' : r >= idx - 0.5 ? 'bi bi-star-half' : 'bi bi-star';
    });
  };

  if (ratingStars && ratingInput) {
    for (let i = 0; i < 5; i++) {
      const star = document.createElement('i');
      star.className = 'bi bi-star';
      star.dataset.index = i;
      ratingStars.appendChild(star);
    }
    ratingStars.addEventListener('click', e => {
      const star = e.target.closest('i');
      if (!star) return;
      const rect = star.getBoundingClientRect();
      const half = (e.clientX - rect.left) > rect.width / 2 ? 1 : 0.5;
      const val = parseInt(star.dataset.index) + half;
      setRating(val);
      applyFilters();
    });
    ratingStars.addEventListener('keydown', e => {
      const curr = toNumber(ratingInput.value) || 0;
      if (e.key === 'ArrowRight') {
        setRating(Math.min(curr + 0.5, 5));
        applyFilters();
        e.preventDefault();
      } else if (e.key === 'ArrowLeft') {
        setRating(Math.max(curr - 0.5, 0));
        applyFilters();
        e.preventDefault();
      } else if (e.key === ' ' || e.key === 'Enter') {
        setRating(0);
        applyFilters();
        e.preventDefault();
      }
    });
    updateRatingDisplay();
  }

  if (chipsContainer) {
    const allCategories = [
      "Cocktail classico",
      "Mixology&Signature",
      "Enoteca/Vineria (Merlot)",
      "Birreria artigianale",
      "Pub/Irish pub",
      "Gastropub",
      "Sports bar",
      "Lounge bar",
      "Rooftop/Sky bar",
      "Speakeasy",
      "Live music/Jazz bar",
      "Piano bar",
      "Karaoke bar",
      "Club/Discoteca bar",
      "Aperitivo&Cicchetti",
      "Caffetteria/Espresso bar",
      "Pasticceria-bar",
      "Paninoteca/Snack bar",
      "Gelateria-bar",
      "Bar di paese",
      "Lakefront/Lido (lago)",
      "Grotto ticinese",
      "Hotel bar",
      "Shisha/Hookah lounge",
      "Cigar&Whisky lounge",
      "Gin bar",
      "Rum/Tiki bar",
      "Tequila/Mezcalería",
      "Biliardo&Darts pub",
      "Afterwork/Business bar",
    ];
    allCategories.forEach(c => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.dataset.value = norm(c);
      chip.textContent = c;
      chipsContainer.appendChild(chip);
    });
    chipsContainer.addEventListener('click', e => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      const val = chip.dataset.value;
      if (activeCategories.has(val)) {
        activeCategories.delete(val);
        chip.classList.remove('active');
      } else {
        activeCategories.add(val);
        chip.classList.add('active');
      }
      applyFilters();
    });
  }

  function updateActiveChips() {
    if (!activeChips) return;
    activeChips.innerHTML = '';
    const qName = norm(nameInput?.value);
    const qCity = norm(cityInput?.value);
    const maxDist = toNumber(distInput?.value);
    const maxDefault = toNumber(distInput?.max || 30);
    const useDist = maxDist != null && maxDist < maxDefault;
    const minRating = toNumber(ratingInput?.value);
    const showOpen = openCheck?.checked;
    const showClosed = closedCheck?.checked;
    if (qName) addChip('name', 'Nome del bar', nameInput.value);
    if (qCity) addChip('city', 'Città', cityInput.value);
    if (useDist) addChip('distance', 'Distanza ≤', distInput.value + ' km');
    if (minRating != null) addChip('rating', 'Rating ≥', minRating.toFixed(1));
    if (showOpen) addChip('open', 'Aperti ora', '');
    if (showClosed) addChip('closed', 'Chiusi ora', '');
    activeCategories.forEach(val => {
      const label = chipsContainer?.querySelector(`.chip[data-value="${val}"]`)?.textContent || val;
      addChip('category', 'Categoria', label, val);
    });
  }

  function addChip(type, label, value, val) {
    if (!activeChips) return;
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'filter-chip';
    chip.dataset.filter = type;
    if (val) chip.dataset.value = val;
    chip.innerHTML = label + (value ? ': ' + value : '') + ' <i class="bi bi-x" aria-hidden="true"></i>';
    activeChips.appendChild(chip);
  }

  function applyFilters() {
    const qName = norm(nameInput?.value);
    const qCity = norm(cityInput?.value);
    const maxDist = toNumber(distInput?.value);
    const maxDefault = toNumber(distInput?.max || 30);
    const useDist = maxDist != null && maxDist < maxDefault;
    const minRating = toNumber(ratingInput?.value);
    const showOpen = openCheck?.checked;
    const showClosed = closedCheck?.checked;
    cards.forEach(card => {
      const data = card.dataset;
      let show = true;
      if (qName && !norm(data.name).includes(qName)) show = false;
      if (qCity && !norm(data.city).includes(qCity)) show = false;
      const dist = toNumber(data.distance_km);
      if (useDist && (dist == null || dist > maxDist)) show = false;
      const rating = toNumber(data.rating);
      if (minRating != null && (rating == null || rating < minRating)) show = false;
      const isOpen = data.open === 'true';
      if (showOpen && !isOpen) show = false;
      if (showClosed && isOpen) show = false;
      if (activeCategories.size > 0) {
        const barCats = (data.categories || '').split(',').map(norm);
        if (!barCats.some(c => activeCategories.has(c))) show = false;
      }
      card.closest('li').hidden = !show;
    });
    const activeCount = (qName ? 1 : 0) + (qCity ? 1 : 0) + (useDist ? 1 : 0) + (minRating != null ? 1 : 0) + (showOpen ? 1 : 0) + (showClosed ? 1 : 0) + activeCategories.size;
    if (filterBadge) {
      filterBadge.textContent = activeCount;
      filterBadge.hidden = activeCount === 0;
    }
    updateActiveChips();
  }

  const debouncedApply = debounce(applyFilters, 250);
  nameInput?.addEventListener('input', debouncedApply);
  cityInput?.addEventListener('input', debouncedApply);
  if (distInput) {
    const updateDist = () => {
      distanceValue.textContent = distInput.value + ' km';
      applyFilters();
    };
    distInput.addEventListener('input', throttle(updateDist, 100));
  }
  if (ratingInput) {
    // rating changes handled in setRating
  }
  [openCheck, closedCheck].forEach(el => el?.addEventListener('change', applyFilters));

  activeChips?.addEventListener('click', e => {
    const chip = e.target.closest('.filter-chip');
    if (!chip) return;
    const type = chip.dataset.filter;
    if (type === 'name') nameInput.value = '';
    else if (type === 'city') cityInput.value = '';
    else if (type === 'distance') {
      distInput.value = distInput.max;
      distanceValue.textContent = distInput.value + ' km';
    } else if (type === 'rating') setRating(0);
    else if (type === 'open') openCheck.checked = false;
    else if (type === 'closed') closedCheck.checked = false;
    else if (type === 'category') {
      const val = chip.dataset.value;
      activeCategories.delete(val);
      const catChip = chipsContainer?.querySelector(`.chip[data-value="${val}"]`);
      catChip?.classList.remove('active');
    }
    applyFilters();
  });

  document.getElementById('clearFilters')?.addEventListener('click', () => {
    if (nameInput) nameInput.value = '';
    if (cityInput) cityInput.value = '';
    if (distInput) {
      distInput.value = distInput.max;
      distanceValue.textContent = distInput.value + ' km';
    }
    setRating(0);
    if (openCheck) openCheck.checked = false;
    if (closedCheck) closedCheck.checked = false;
    activeCategories.clear();
    chipsContainer?.querySelectorAll('.chip.active').forEach(ch => ch.classList.remove('active'));
    applyFilters();
  });

  document.getElementById('applyFiltersBtn')?.addEventListener('click', applyFilters);

  applyFilters();

  function sortByDistance(lat, lng) {
    cards.forEach(card => {
      const bLat = toNumber(card.dataset.latitude);
      const bLng = toNumber(card.dataset.longitude);
      if (bLat != null && bLng != null) {
        const dist = haversineKm(lat, lng, bLat, bLng);
        card.dataset.distance_km = dist;
        renderMeta(card, { rating: card.dataset.rating, distance_km: dist });
      } else {
        renderMeta(card, { rating: card.dataset.rating, distance_km: null });
      }
    });
    const items = cards.map(c => c.closest('li'));
    items.sort((a, b) => {
      const da = toNumber(a.querySelector('.bar-card').dataset.distance_km);
      const db = toNumber(b.querySelector('.bar-card').dataset.distance_km);
      return (da == null ? Infinity : da) - (db == null ? Infinity : db);
    });
    items.forEach(li => list.appendChild(li));
    applyFilters();
  }
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      sortByDistance(pos.coords.latitude, pos.coords.longitude);
    });
  } else {
    cards.forEach(card => renderMeta(card, card.dataset));
    applyFilters();
  }
});
