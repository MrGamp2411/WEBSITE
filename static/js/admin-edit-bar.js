(function(){
  function toNumber(value, fallback) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function updateLatLngInputs(position) {
    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');
    if (latInput) {
      latInput.value = position.lat.toFixed(6);
    }
    if (lngInput) {
      lngInput.value = position.lng.toFixed(6);
    }
  }

  function initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl || typeof L === 'undefined') return;
    const initialLat = toNumber(mapEl.dataset.initialLat, 0);
    const initialLng = toNumber(mapEl.dataset.initialLng, 0);
    const map = L.map(mapEl).setView([initialLat, initialLng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    const marker = L.marker([initialLat, initialLng], { draggable: true }).addTo(map);
    marker.on('dragend', (event) => {
      updateLatLngInputs(event.target.getLatLng());
    });
    updateLatLngInputs(marker.getLatLng());
  }

  function initCategoryChips() {
    const select = document.getElementById('categoriesNative');
    const mount = document.getElementById('categoriesChips');
    const countEl = document.getElementById('catCount');
    const countTemplate = countEl?.dataset.template || '{selected}/{max}';
    const countMax = Number.parseInt(countEl?.dataset.max || '5', 10);
    if (!select || !mount) return;

    const MAX = Number.isFinite(countMax) ? countMax : 5;
    const all = Array.from(select.options).map((option) => ({
      value: option.value,
      label: option.text,
      selected: option.selected
    }));

    const selectedCount = () => all.filter((item) => item.selected).length;

    function syncSelect() {
      all.forEach((item) => {
        const option = Array.from(select.options).find((opt) => opt.value === item.value);
        if (option) option.selected = item.selected;
      });
    }

    function render() {
      mount.innerHTML = '';
      const count = selectedCount();
      if (countEl) {
        countEl.textContent = countTemplate
          .replace('{selected}', String(count))
          .replace('{max}', String(MAX));
      }
      const limitReached = count >= MAX;

      all.forEach((item) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'chip-btn';
        button.setAttribute('aria-pressed', item.selected ? 'true' : 'false');
        button.textContent = item.label;
        if (limitReached && !item.selected) {
          button.disabled = true;
        }
        button.addEventListener('click', () => {
          if (!item.selected && selectedCount() >= MAX) return;
          item.selected = !item.selected;
          syncSelect();
          render();
        });
        button.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            button.click();
          }
        });
        mount.appendChild(button);
      });
    }

    render();
  }

  function initManualCloseToggle() {
    const closeCheckbox = document.getElementById('manual_closed');
    const hoursWrap = document.querySelector('.hours-table');
    if (!closeCheckbox || !hoursWrap) return;

    function applyDisabledState() {
      const disabled = closeCheckbox.checked;
      hoursWrap.classList.toggle('hours-disabled', disabled);
      hoursWrap.querySelectorAll('input[type="time"]').forEach((input) => {
        input.disabled = disabled;
      });
    }

    applyDisabledState();
    closeCheckbox.addEventListener('change', applyDisabledState);
  }

  document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initCategoryChips();
    initManualCloseToggle();
  });
})();
