function formatPayment(method) {
  return method ? method.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()) : '';
}

function initBartender(barId) {
  const list = document.getElementById('orders');
  function render(order) {
    let li = document.getElementById('order-' + order.id);
    if (!li) {
      li = document.createElement('li');
      li.id = 'order-' + order.id;
      li.className = 'card';
      list.appendChild(li);
    }
    let actions = '';
    if (order.status === 'pending') {
      actions = `<button data-status="preparing">Accept</button>`;
    } else if (order.status === 'preparing') {
      actions = `<button data-status="ready">Ready</button>`;
    } else if (order.status === 'ready') {
      actions = `<button data-status="completed">Complete</button>`;
    }
    const actionsHtml = actions ? `<div class="order-actions">${actions}</div>` : '';
    li.innerHTML =
      `<div class="card__body">` +
      `<h3 class="card__title">Order #${order.id} - <span class=\"status\">${order.status}</span></h3>` +
      `<p>Customer: ${order.customer_name || ''} (${order.customer_prefix || ''} ${order.customer_phone || ''})</p>` +
      `<p>Bar: ${order.bar_name || ''}</p>` +
      `<p>Table: ${order.table_name || ''}</p>` +
      `<p>Payment: ${formatPayment(order.payment_method)}</p>` +
      `<p>Total: CHF ${order.total.toFixed(2)}</p>` +
      `<ul>` +
      order.items.map(i => `<li>${i.qty}× ${i.menu_item_name || ''}</li>`).join('') +
      `</ul>` +
      actionsHtml +
      `</div>`;
    li.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => updateStatus(order.id, btn.dataset.status));
    });
    if (order.status === 'completed') {
      li.remove();
    }
  }
  fetch(`/api/bars/${barId}/orders`).then(r => r.json()).then(data => data.forEach(render));
  const ws = new WebSocket(`ws://${location.host}/ws/bar/${barId}/orders`);
  ws.onmessage = ev => {
    const data = JSON.parse(ev.data);
    if (data.type === 'order') {
      render(data.order);
    }
  };
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
    li.innerHTML =
      `<div class="card__body">` +
      `<h3 class="card__title">Order #${order.id} - <span class=\"status\">${order.status}</span></h3>` +
      `<p>Customer: ${order.customer_name || ''} (${order.customer_prefix || ''} ${order.customer_phone || ''})</p>` +
      `<p>Bar: ${order.bar_name || ''}</p>` +
      `<p>Table: ${order.table_name || ''}</p>` +
      `<p>Payment: ${formatPayment(order.payment_method)}</p>` +
      `<p>Total: CHF ${order.total.toFixed(2)}</p>` +
      `<ul>` +
      order.items.map(i => `<li>${i.qty}× ${i.menu_item_name || ''}</li>`).join('') +
      `</ul>` +
      `</div>`;
    return li;
  }
  const ws = new WebSocket(`ws://${location.host}/ws/user/${userId}/orders`);
  ws.onmessage = ev => {
    const data = JSON.parse(ev.data);
    if (data.type === 'order') {
      const li = render(data.order);
      if (data.order.status === 'completed') {
        completed.appendChild(li);
      } else {
        pending.appendChild(li);
      }
    }
  };
}

function updateStatus(orderId, status) {
  fetch(`/api/orders/${orderId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  });
}
