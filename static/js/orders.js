function formatPayment(method) {
  return method ? method.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()) : '';
}

function formatStatus(status) {
  return status ? status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()) : '';
}

function formatTime(dt) {
  if (!dt) return '';
  const d = new Date(dt + 'Z');
  const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return `${date} ${time}`;
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

  function insertSorted(container, element, ascending) {
    const created = new Date(element.dataset.createdAt + 'Z');
    const children = Array.from(container.children);
    const index = children.findIndex(child => {
      const childCreated = new Date(child.dataset.createdAt + 'Z');
      return ascending ? childCreated > created : childCreated < created;
    });
    if (index === -1) {
      container.appendChild(element);
    } else {
      container.insertBefore(element, children[index]);
    }
  }

  function render(order) {
    let el = document.getElementById('order-' + order.id);
    if (!el) {
      el = document.createElement('article');
      el.id = 'order-' + order.id;
    }
    let actions = '';
    if (order.status === 'PLACED') {
      actions = `<button data-status="ACCEPTED">Accept</button><button data-status="CANCELED">Cancel</button>`;
    } else if (order.status === 'ACCEPTED') {
      actions = `<button data-status="READY">Ready</button>`;
    } else if (order.status === 'READY') {
      actions = `<button data-status="COMPLETED">Complete</button>`;
    }
    const actionsHtml = actions ? `<div class="order-actions">${actions}</div>` : '';
    const placed = formatTime(order.created_at);
    const refund = order.status === 'CANCELED' && order.refund_amount ? `<div><dt>Refunded</dt><dd class="num nowrap">CHF ${order.refund_amount.toFixed(2)}</dd></div>` : '';
    const notes = order.notes ? `<div><dt>Notes</dt><dd>${order.notes}</dd></div>` : '';
    const prep = order.ready_at ? `<div><dt>Prep time</dt><dd class="num">${diffMinutes(order.created_at, order.ready_at)} min</dd></div>` : '';
    el.className = 'order-card card card--' + order.status.toLowerCase();
    el.setAttribute('role', 'article');
    el.setAttribute('aria-labelledby', 'order-' + order.id + '-title');
    el.dataset.status = order.status;
    el.dataset.createdAt = order.created_at;
    el.innerHTML =
      `<header class="order-card__header">` +
      `<h3 id="order-${order.id}-title">Order ${order.public_order_code || ('#' + order.id)}</h3>` +
      `<span class="order-status chip status status-${order.status.toLowerCase()}" aria-label="Order status: ${formatStatus(order.status)}">${formatStatus(order.status)}</span>` +
      `</header>` +
      `<div class="order-card__divider"></div>` +
      `<section class="order-card__meta"><dl class="order-kv">` +
      `<div><dt>Total</dt><dd class="num nowrap">CHF ${order.total.toFixed(2)}</dd></div>` +
      refund +
      `<div><dt>Placed</dt><dd class="num nowrap">${placed}</dd></div>` +

      `<div><dt>Customer</dt><dd>${order.customer_name || ''} <a href="tel:${(order.customer_prefix || '').replace(/\s+/g,'')}${(order.customer_phone || '').replace(/\s+/g,'')}">(${order.customer_prefix || ''} ${order.customer_phone || ''})</a></dd></div>` +
      `<div><dt>Bar</dt><dd>${order.bar_name || ''}</dd></div>` +

      `<div><dt>Table</dt><dd>${order.table_name || ''}</dd></div>` +
      `<div><dt>Payment</dt><dd>${formatPayment(order.payment_method)}</dd></div>` +
      notes +
      prep +
      `</dl></section>` +
      `<div class="order-card__divider"></div>` +
      `<section class="order-card__items"><ul class="order-items">` +
      order.items.map(i => `<li><span class="qty">${i.qty}×</span><span class="name">${i.menu_item_name || ''}</span></li>`).join('') +
      `</ul>` +
      actionsHtml +
      `</section>`;
    el.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => updateStatus(order.id, btn.dataset.status, render));
    });
    if (order.status === 'PLACED') {
      insertSorted(incoming, el, true);
    } else if (order.status === 'ACCEPTED') {
      insertSorted(preparing, el, true);
    } else if (order.status === 'READY') {
      insertSorted(ready, el, true);
    } else if (
      order.status === 'COMPLETED' ||
      order.status === 'CANCELED' ||
      order.status === 'REJECTED'
    ) {
      insertSorted(completed, el, false);
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
    let el = document.getElementById('user-order-' + order.id);
    if (!el) {
      el = document.createElement('article');
      el.id = 'user-order-' + order.id;
    }
    el.className = 'order-card card card--' + order.status.toLowerCase();
    el.setAttribute('role', 'article');
    el.setAttribute('aria-labelledby', 'order-' + order.id + '-title');
    el.dataset.status = order.status;
    const placed = formatTime(order.created_at);
    const refund = order.status === 'CANCELED' && order.refund_amount ? `<div><dt>Refunded</dt><dd class="num nowrap">CHF ${order.refund_amount.toFixed(2)}</dd></div>` : '';
    const notes = order.notes ? `<div><dt>Notes</dt><dd>${order.notes}</dd></div>` : '';
    const prep = order.ready_at ? `<div><dt>Prep time</dt><dd class="num">${diffMinutes(order.created_at, order.ready_at)} min</dd></div>` : '';
    const actions = order.status === 'PLACED'
      ? `<div class="order-actions"><button data-order-id="${order.id}" data-status="CANCELED">Cancel</button></div>`
      : '';
    el.innerHTML =
      `<header class="order-card__header">` +
      `<h3 id="order-${order.id}-title">Order ${order.public_order_code || ('#' + order.id)}</h3>` +
      `<span class="order-status chip status status-${order.status.toLowerCase()}" aria-label="Order status: ${formatStatus(order.status)}">${formatStatus(order.status)}</span>` +
      `</header>` +
      `<div class="order-card__divider"></div>` +
      `<section class="order-card__meta"><dl class="order-kv">` +
      `<div><dt>Total</dt><dd class="num nowrap">CHF ${order.total.toFixed(2)}</dd></div>` +
      refund +
      `<div><dt>Placed</dt><dd class="num nowrap">${placed}</dd></div>` +

      `<div><dt>Customer</dt><dd>${order.customer_name || ''} <a href="tel:${(order.customer_prefix || '').replace(/\s+/g,'')}${(order.customer_phone || '').replace(/\s+/g,'')}">(${order.customer_prefix || ''} ${order.customer_phone || ''})</a></dd></div>` +
      `<div><dt>Bar</dt><dd>${order.bar_name || ''}</dd></div>` +

      `<div><dt>Table</dt><dd>${order.table_name || ''}</dd></div>` +
      `<div><dt>Payment</dt><dd>${formatPayment(order.payment_method)}</dd></div>` +
      notes +
      prep +
      `</dl></section>` +
      `<div class="order-card__divider"></div>` +
      `<section class="order-card__items"><ul class="order-items">` +
      order.items.map(i => `<li><span class="qty">${i.qty}×</span><span class="name">${i.menu_item_name || ''}</span></li>`).join('') +
      `</ul>` +
      actions +
      `</section>`;
    return el;
  }
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${protocol}://${location.host}/ws/user/${userId}/orders`);
  ws.onmessage = ev => {
    const data = JSON.parse(ev.data);
    if (data.type === 'order') {
      const card = render(data.order);
      if (
        ['COMPLETED', 'CANCELED', 'REJECTED'].includes(data.order.status)
      ) {
        completed.appendChild(card);
      } else {
        pending.appendChild(card);
      }
    }
  };
  pending.addEventListener('click', e => {
    const btn = e.target.closest('button[data-status]');
    if (btn) {
      updateStatus(btn.dataset.orderId, btn.dataset.status);
    }
  });
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
