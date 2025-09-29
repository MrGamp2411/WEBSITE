(function () {
  function readJson(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      console.error('Failed to parse JSON from #' + id, err);
      return null;
    }
  }

  var layoutState = readJson('layoutState');
  if (layoutState) {
    window.orderingPaused = Boolean(layoutState.orderingPaused);
    window.showServicePausedOnLoad = Boolean(layoutState.showServicePausedOnLoad);
  }

  var appI18n = readJson('appI18nData');
  if (appI18n) {
    window.APP_I18N = appI18n;
  }
})();
