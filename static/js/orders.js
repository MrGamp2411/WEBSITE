function initBartender(barId) {
  const list = document.getElementById('orders');
  function render(order) {
    let li = document.getElementById('order-' + order.id);
    if (!li) {
      li = document.createElement('li');
      li.id = 'order-' + order.id;
      li.innerHTML = `Order #${order.id} - <span class="status">${order.status}</span> ` +
        `<button data-status="preparing">Accept</button> ` +
        `<button data-status="ready">Ready</button> ` +
        `<button data-status="completed">Complete</button>`;
      list.appendChild(li);
      li.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => updateStatus(order.id, btn.dataset.status));
      });
    } else {
      li.querySelector('.status').textContent = order.status;
      if (order.status === 'completed') {
        li.remove();
      }
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
  const ws = new WebSocket(`ws://${location.host}/ws/user/${userId}/orders`);
  ws.onmessage = ev => {
    const data = JSON.parse(ev.data);
    if (data.type === 'order') {
      let li = document.getElementById('user-order-' + data.order.id);
      if (li) {
        li.querySelector('.status').textContent = data.order.status;
        if (data.order.status === 'completed') {
          completed.appendChild(li);
        }
      } else if (data.order.status !== 'completed') {
        li = document.createElement('li');
        li.id = 'user-order-' + data.order.id;
        li.innerHTML = `Order #${data.order.id} - <span class="status">${data.order.status}</span>`;
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
