function initDisplay(barId) {
  const preparing = document.getElementById('preparing-orders');
  const ready = document.getElementById('ready-orders');
  const APP_I18N = window.APP_I18N || {};
  const displayTexts = APP_I18N.display || {};
  function formatTemplate(template, values){
    if(typeof template !== 'string') return '';
    return template.replace(/\{(\w+)\}/g, (_, key) => Object.prototype.hasOwnProperty.call(values, key) ? values[key] : '');
  }

  function render(order) {
    let el = document.getElementById('order-' + order.id);
    if (!el) {
      el = document.createElement('article');
      el.id = 'order-' + order.id;
    }
    el.className = 'order-card card card--' + order.status.toLowerCase();
    const code = order.public_order_code || ('#' + order.id);
    const title = formatTemplate(displayTexts.card_title, { code }) || `Order ${code}`;
    el.innerHTML = `<header class="order-card__header"><h3>${title}</h3></header>`;
    if (order.status === 'ACCEPTED') {
      preparing.appendChild(el);
    } else if (order.status === 'READY') {
      ready.appendChild(el);
    } else {
      el.remove();
    }
  }

  function load() {
    fetch(`/api/bars/${barId}/orders`).then(r => r.json()).then(data => data.forEach(render));
  }

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${protocol}://${location.host}/ws/bar/${barId}/orders`);
    let ping;
    ws.onopen = () => {
      load();
      ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
    };
    ws.onmessage = ev => {
      const data = JSON.parse(ev.data);
      if (data.type === 'order') {
        render(data.order);
      }
    };
    ws.onclose = () => {
      if (ping) clearInterval(ping);
      setTimeout(connect, 1000);
    };
    ws.onerror = () => ws.close();
  }
  connect();
}
