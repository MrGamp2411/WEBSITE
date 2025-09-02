function formatPayment(method) {
  return method ? method.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()) : '';
}

function formatStatus(status) {
  return status ? status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()) : '';
}

function formatTime(dt) {
  if (!dt) return '';
  const d = new Date(dt + 'Z');
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function diffMinutes(start, end) {
  if (!start || !end) return 0;
  return Math.round((new Date(end + 'Z') - new Date(start + 'Z')) / 60000);
}

function initBartender(barId) {
  const incoming = document.getElementById('incoming-orders');
  const preparing = document.getElementById('preparing-orders');
  const ready = document.getElementById('ready-orders');
  const completed = document.getElementById('completed-orders');
  function render(order) {
    let li = document.getElementById('order-' + order.id);
    if (!li) {
      li = document.createElement('li');
      li.id = 'order-' + order.id;
      li.className = 'card';
    }
    let actions = '';
    if (order.status === 'PLACED') {
      actions = `<button data-status="ACCEPTED">Accept</button>`;
    } else if (order.status === 'ACCEPTED') {
      actions = `<button data-status="READY">Ready</button>`;
    } else if (order.status === 'READY') {
      actions = `<button data-status="COMPLETED">Complete</button>`;
    }
    const actionsHtml = actions ? `<div class="order-actions">${actions}</div>` : '';
    const placed = formatTime(order.created_at);
    const prep = order.ready_at ? `<p>Prep time: ${diffMinutes(order.created_at, order.ready_at)} min</p>` : '';
    const notes = order.notes ? `<p>Notes: ${order.notes}</p>` : '';
    li.className = 'card card--' + order.status.toLowerCase();
    li.innerHTML =
      `<div class="card__body">` +
      `<h3 class="card__title">Order #${order.id} - <span class=\"status status-${order.status.toLowerCase()}\">${formatStatus(order.status)}</span></h3>` +
      `<p>Customer: ${order.customer_name || ''} (${order.customer_prefix || ''} ${order.customer_phone || ''})</p>` +
      `<p>Bar: ${order.bar_name || ''}</p>` +
      `<p>Table: ${order.table_name || ''}</p>` +
      `<p>Payment: ${formatPayment(order.payment_method)}</p>` +
      `<p>Total: CHF ${order.total.toFixed(2)}</p>` +
      `<p>Placed: ${placed}</p>` +
      prep +
      notes +
      `<ul>` +
      order.items.map(i => `<li>${i.qty}× ${i.menu_item_name || ''}</li>`).join('') +
      `</ul>` +
      actionsHtml +
      `</div>`;
    li.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => updateStatus(order.id, btn.dataset.status, render));
    });
    if (order.status === 'PLACED') {
      incoming.prepend(li);
    } else if (order.status === 'ACCEPTED') {
      preparing.prepend(li);
    } else if (order.status === 'READY') {
      ready.prepend(li);
    } else if (order.status === 'COMPLETED') {
      completed.prepend(li);
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
      if (ping) {
        clearInterval(ping);
      }
      setTimeout(connect, 1000);
    };
    ws.onerror = () => ws.close();
  }
  connect();
}

function initUser(userId) {
  const pending = document.getElementById('pending-orders');
  const completed = document.getElementById('completed-orders');
  function render(order) {
    let li = document.getElementById('user-order-' + order.id);
    if (!li) {
      li = document.createElement('li');
      li.id = 'user-order-' + order.id;
      li.className = 'card';
    }
    li.className = 'card card--' + order.status.toLowerCase();
    const placed = formatTime(order.created_at);
    const prep = order.ready_at ? `<p>Prep time: ${diffMinutes(order.created_at, order.ready_at)} min</p>` : '';
    const notes = order.notes ? `<p>Notes: ${order.notes}</p>` : '';
    li.innerHTML =
      `<div class="card__body">` +
      `<h3 class="card__title">Order #${order.id} - <span class=\"status status-${order.status.toLowerCase()}\">${formatStatus(order.status)}</span></h3>` +
      `<p>Customer: ${order.customer_name || ''} (${order.customer_prefix || ''} ${order.customer_phone || ''})</p>` +
      `<p>Bar: ${order.bar_name || ''}</p>` +
      `<p>Table: ${order.table_name || ''}</p>` +
      `<p>Payment: ${formatPayment(order.payment_method)}</p>` +
      `<p>Total: CHF ${order.total.toFixed(2)}</p>` +
      `<p>Ordered at: ${placed}</p>` +
      prep +
      notes +
      `<ul>` +
      order.items.map(i => `<li>${i.qty}× ${i.menu_item_name || ''}</li>`).join('') +
      `</ul>` +
      `</div>`;
    return li;
  }
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${protocol}://${location.host}/ws/user/${userId}/orders`);
  ws.onmessage = ev => {
    const data = JSON.parse(ev.data);
    if (data.type === 'order') {
      const li = render(data.order);
      if (data.order.status === 'COMPLETED') {
        completed.appendChild(li);
      } else {
        pending.appendChild(li);
      }
    }
  };
}

function updateStatus(orderId, status, onUpdate) {
  fetch(`/api/orders/${orderId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  })
    .then(r => r.json())
    .then(data => {
      if (onUpdate && data.order) {
        onUpdate(data.order);
      }
    });
}
