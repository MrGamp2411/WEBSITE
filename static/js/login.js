(function () {
  var latInput = document.getElementById('latitude');
  var lngInput = document.getElementById('longitude');
  if (!latInput || !lngInput) {
    return;
  }

  if (!navigator.geolocation) {
    return;
  }

  navigator.geolocation.getCurrentPosition(function (pos) {
    if (pos && pos.coords) {
      latInput.value = pos.coords.latitude;
      lngInput.value = pos.coords.longitude;
    }
  });
})();
