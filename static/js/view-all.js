function toNumber(v) {
  if (v == null) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  const m = String(v).replace(',', '.').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
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
  }
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      sortByDistance(pos.coords.latitude, pos.coords.longitude);
    });
  } else {
    cards.forEach(card => renderMeta(card, card.dataset));
  }
});
