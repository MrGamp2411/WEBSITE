function toNumber(v) {
  if (v == null) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  const m = String(v).replace(',', '.').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
}

const norm = s => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

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
  const openCheck = document.getElementById('filterOpen');
  const closedCheck = document.getElementById('filterClosed');
  const chipsContainer = document.getElementById('categoryChips');
  const activeCategories = new Set();

  if (chipsContainer) {
    const catSet = new Set();
    cards.forEach(card => {
      (card.dataset.categories || '').split(',').map(norm).filter(Boolean).forEach(c => catSet.add(c));
    });
    Array.from(catSet).sort().forEach(c => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.dataset.value = c;
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

  function applyFilters() {
    const qName = norm(nameInput?.value);
    const qCity = norm(cityInput?.value);
    const maxDist = toNumber(distInput?.value);
    const minRating = toNumber(ratingInput?.value);
    const showOpen = openCheck?.checked;
    const showClosed = closedCheck?.checked;
    cards.forEach(card => {
      const data = card.dataset;
      let show = true;
      if (qName && !norm(data.name).includes(qName)) show = false;
      if (qCity && !norm(data.city).includes(qCity)) show = false;
      const dist = toNumber(data.distance_km);
      if (maxDist != null && (dist == null || dist > maxDist)) show = false;
      const rating = toNumber(data.rating);
      if (minRating != null && (rating == null || rating < minRating)) show = false;
      const isOpen = data.open === 'true';
      if (showOpen !== showClosed) {
        if (showOpen && !isOpen) show = false;
        if (showClosed && isOpen) show = false;
      }
      if (activeCategories.size > 0) {
        const barCats = (data.categories || '').split(',').map(norm);
        if (!barCats.some(c => activeCategories.has(c))) show = false;
      }
      card.closest('li').hidden = !show;
    });
  }

  [nameInput, cityInput, distInput, ratingInput].forEach(el => el?.addEventListener('input', applyFilters));
  [openCheck, closedCheck].forEach(el => el?.addEventListener('change', applyFilters));

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
