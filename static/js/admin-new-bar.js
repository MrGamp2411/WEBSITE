(function () {
  function initMap() {
    if (typeof L === 'undefined') {
      return;
    }
    var mapEl = document.getElementById('map');
    var latInput = document.getElementById('latitude');
    var lngInput = document.getElementById('longitude');
    if (!mapEl || !latInput || !lngInput) {
      return;
    }

    var initialLat = 45.4642;
    var initialLng = 9.19;
    var map = L.map('map').setView([initialLat, initialLng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    var marker = L.marker([initialLat, initialLng], { draggable: true }).addTo(map);

    function updateInputs(e) {
      var pos = e.target.getLatLng();
      latInput.value = pos.lat.toFixed(6);
      lngInput.value = pos.lng.toFixed(6);
    }

    marker.on('dragend', updateInputs);
    updateInputs({ target: marker });
  }

  function initCategoryChips() {
    var select = document.getElementById('categoriesNative');
    var mount = document.getElementById('categoriesChips');
    if (!select || !mount) {
      return;
    }

    var countEl = document.getElementById('catCount');
    var countTemplate = (countEl && countEl.dataset.template) || '{selected}/{max}';
    var countMax = Number((countEl && countEl.dataset.max) || 5) || 5;
    var options = Array.prototype.map.call(select.options, function (opt) {
      return { value: opt.value, label: opt.text, selected: opt.selected };
    });

    function selectedCount() {
      return options.filter(function (item) { return item.selected; }).length;
    }

    function syncSelect() {
      options.forEach(function (item) {
        Array.prototype.forEach.call(select.options, function (opt) {
          if (opt.value === item.value) {
            opt.selected = item.selected;
          }
        });
      });
    }

    function render() {
      mount.innerHTML = '';
      var count = selectedCount();
      if (countEl) {
        countEl.textContent = countTemplate.replace('{selected}', count).replace('{max}', countMax);
      }
      var limitReached = count >= countMax;

      options.forEach(function (item) {
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'chip' + (item.selected ? ' chip--selected' : '');
        button.textContent = item.label;
        button.setAttribute('aria-pressed', item.selected ? 'true' : 'false');
        button.addEventListener('click', function () {
          if (item.selected) {
            item.selected = false;
          } else if (!limitReached) {
            item.selected = true;
          }
          syncSelect();
          render();
        });
        mount.appendChild(button);
      });
    }

    render();
  }

  initMap();
  initCategoryChips();
})();
