const APP_I18N = window.APP_I18N || {};
const ORDERS_I18N = APP_I18N.orders || {};
const CARD_TEXTS = ORDERS_I18N.card || {};
const ACTION_TEXTS = ORDERS_I18N.actions || {};
const STATUS_TEXTS = ORDERS_I18N.statuses || {};
const PAYMENT_TEXTS = ORDERS_I18N.payment_methods || {};
const REASON_TEXTS = CARD_TEXTS.cancellation_reasons || {};

function escapeHtml(value) {
  if (value == null) {
    return '';
  }
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatTemplate(template, values){
  if(typeof template !== 'string') return '';
  return template.replace(/\{(\w+)\}/g, (_, key) => Object.prototype.hasOwnProperty.call(values, key) ? values[key] : '');
}

function getField(name, fallback){
  return CARD_TEXTS.fields && Object.prototype.hasOwnProperty.call(CARD_TEXTS.fields, name)
    ? CARD_TEXTS.fields[name]
    : fallback;
}

function getAction(name, fallback){
  return Object.prototype.hasOwnProperty.call(ACTION_TEXTS, name) ? ACTION_TEXTS[name] : fallback;
}

function formatPayment(method) {
  if(!method) return '';
  const key = method.toLowerCase();
  if(Object.prototype.hasOwnProperty.call(PAYMENT_TEXTS, key)){
    return PAYMENT_TEXTS[key];
  }
  return method.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatCancellationReason(reason) {
  if (!reason) return '';
  const key = reason.toLowerCase();
  if (Object.prototype.hasOwnProperty.call(REASON_TEXTS, key)) {
    return REASON_TEXTS[key];
  }
  return reason.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatStatus(status) {
  if(!status) return '';
  if(Object.prototype.hasOwnProperty.call(STATUS_TEXTS, status)){
    return STATUS_TEXTS[status];
  }
  return status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
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
    const code = order.public_order_code || ('#' + order.id);
    let actions = '';
    if (order.status === 'PLACED') {
      actions = `<button data-status="ACCEPTED">${getAction('accept', 'Accept')}</button><button data-status="CANCELED">${getAction('cancel', 'Cancel')}</button>`;
    } else if (order.status === 'ACCEPTED') {
      actions = `<button data-status="READY">${getAction('ready', 'Ready')}</button>`;
    } else if (order.status === 'READY') {
      actions = `<button data-status="COMPLETED">${getAction('complete', 'Complete')}</button>`;
    }
    const actionsHtml = actions ? `<div class="order-actions">${actions}</div>` : '';
    const placed = formatTime(order.created_at);
    const refund = order.status === 'CANCELED' && order.refund_amount
      ? `<div><dt>${getField('refunded', 'Refunded')}</dt><dd class="num nowrap">CHF ${order.refund_amount.toFixed(2)}</dd></div>`
      : '';
    const cancellation = order.status === 'CANCELED' && order.cancellation_reason
      ? `<div><dt class="order-kv__term--wrap">${getField('cancellation_reason', 'Cancellation reason')}</dt><dd>${formatCancellationReason(order.cancellation_reason)}</dd></div>`
      : '';
    const notes = order.notes
      ? `<div class="order-notes"><dt>${getField('notes', 'Notes')}</dt><dd class="order-notes__value">${escapeHtml(order.notes)}</dd></div>`
      : '';
    const prepMinutes = order.ready_at ? diffMinutes(order.created_at, order.ready_at) : null;
    const prep = prepMinutes != null
      ? `<div><dt>${getField('prep_time', 'Prep time')}</dt><dd class="num">${formatTemplate(CARD_TEXTS.prep_minutes, { minutes: prepMinutes }) || `${prepMinutes} min`}</dd></div>`
      : '';
    el.className = 'order-card card card--' + order.status.toLowerCase();
    el.setAttribute('role', 'article');
    el.setAttribute('aria-labelledby', 'order-' + order.id + '-title');
    el.dataset.status = order.status;
    el.dataset.createdAt = order.created_at;
    const statusLabel = formatStatus(order.status);
    const statusAria = formatTemplate(CARD_TEXTS.status_aria, { status: statusLabel }) || `Order status: ${statusLabel}`;
    const orderTitle = formatTemplate(CARD_TEXTS.title, { code }) || `Order ${code}`;
    const customerName = order.customer_name || (CARD_TEXTS.unknown_customer || 'Unknown');
    const phoneParts = [order.customer_prefix || '', order.customer_phone || ''].filter(Boolean).join(' ');
    const phoneHref = `${(order.customer_prefix || '').replace(/\s+/g,'')}${(order.customer_phone || '').replace(/\s+/g,'')}`;
    const phoneHtml = phoneParts ? ` <a href="tel:${phoneHref}">(${phoneParts})</a>` : '';
    el.innerHTML =
      `<header class="order-card__header">` +
      `<h3 id="order-${order.id}-title">${orderTitle}</h3>` +
      `<span class="order-status chip status status-${order.status.toLowerCase()}" aria-label="${statusAria}">${statusLabel}</span>` +
      `</header>` +
      `<div class="order-card__divider"></div>` +
      `<section class="order-card__meta"><dl class="order-kv">` +
      `<div><dt>${getField('total', 'Total')}</dt><dd class="num nowrap">CHF ${order.total.toFixed(2)}</dd></div>` +
      refund +
      `<div><dt>${getField('placed', 'Placed')}</dt><dd class="num">${placed}</dd></div>` +
      `<div><dt>${getField('customer', 'Customer')}</dt><dd>${customerName}${phoneHtml}</dd></div>` +
      `<div><dt>${getField('bar', 'Bar')}</dt><dd>${order.bar_name || ''}</dd></div>` +
      `<div><dt>${getField('table', 'Table')}</dt><dd>${order.table_name || ''}</dd></div>` +
      `<div><dt>${getField('payment', 'Payment')}</dt><dd>${formatPayment(order.payment_method)}</dd></div>` +
      cancellation +
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
    if (order.notes) {
      const notesValue = el.querySelector('.order-notes__value');
      if (notesValue) {
        notesValue.textContent = order.notes;
      }
    }
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
    const code = order.public_order_code || ('#' + order.id);
    const placed = formatTime(order.created_at);
    const refund = order.status === 'CANCELED' && order.refund_amount
      ? `<div><dt>${getField('refunded', 'Refunded')}</dt><dd class="num nowrap">CHF ${order.refund_amount.toFixed(2)}</dd></div>`
      : '';
    const cancellation = order.status === 'CANCELED' && order.cancellation_reason
      ? `<div><dt class="order-kv__term--wrap">${getField('cancellation_reason', 'Cancellation reason')}</dt><dd>${formatCancellationReason(order.cancellation_reason)}</dd></div>`
      : '';
    const notes = order.notes
      ? `<div><dt>${getField('notes', 'Notes')}</dt><dd class="order-notes__value">${escapeHtml(order.notes)}</dd></div>`
      : '';
    const prepMinutes = order.ready_at ? diffMinutes(order.created_at, order.ready_at) : null;
    const prep = prepMinutes != null
      ? `<div><dt>${getField('prep_time', 'Prep time')}</dt><dd class="num">${formatTemplate(CARD_TEXTS.prep_minutes, { minutes: prepMinutes }) || `${prepMinutes} min`}</dd></div>`
      : '';
    let actionsHtml = '';
    if (order.status === 'PLACED') {
      actionsHtml = `<div class="order-actions"><button data-order-id="${order.id}" data-status="CANCELED">${getAction('cancel', 'Cancel')}</button></div>`;
    } else if (['COMPLETED', 'CANCELED'].includes(order.status)) {
      actionsHtml = `<div class="order-actions"><button class="reorder-order" data-order-id="${order.id}" type="button">${getAction('reorder', 'Reorder')}</button></div>`;
    }
    const statusLabel = formatStatus(order.status);
    const statusAria = formatTemplate(CARD_TEXTS.status_aria, { status: statusLabel }) || `Order status: ${statusLabel}`;
    const orderTitle = formatTemplate(CARD_TEXTS.title, { code }) || `Order ${code}`;
    const customerName = order.customer_name || (CARD_TEXTS.unknown_customer || 'Unknown');
    const phoneParts = [order.customer_prefix || '', order.customer_phone || ''].filter(Boolean).join(' ');
    const phoneHref = `${(order.customer_prefix || '').replace(/\s+/g,'')}${(order.customer_phone || '').replace(/\s+/g,'')}`;
    const phoneHtml = phoneParts ? ` <a href="tel:${phoneHref}">(${phoneParts})</a>` : '';
    el.innerHTML =
      `<header class="order-card__header">` +
      `<h3 id="order-${order.id}-title">${orderTitle}</h3>` +
      `<span class="order-status chip status status-${order.status.toLowerCase()}" aria-label="${statusAria}">${statusLabel}</span>` +
      `</header>` +
      `<div class="order-card__divider"></div>` +
      `<section class="order-card__meta"><dl class="order-kv">` +
      `<div><dt>${getField('total', 'Total')}</dt><dd class="num nowrap">CHF ${order.total.toFixed(2)}</dd></div>` +
      refund +
      `<div><dt>${getField('placed', 'Placed')}</dt><dd class="num">${placed}</dd></div>` +
      `<div><dt>${getField('customer', 'Customer')}</dt><dd>${customerName}${phoneHtml}</dd></div>` +
      `<div><dt>${getField('bar', 'Bar')}</dt><dd>${order.bar_name || ''}</dd></div>` +
      `<div><dt>${getField('table', 'Table')}</dt><dd>${order.table_name || ''}</dd></div>` +
      `<div><dt>${getField('payment', 'Payment')}</dt><dd>${formatPayment(order.payment_method)}</dd></div>` +
      cancellation +
      notes +
      prep +
      `</dl></section>` +
      `<div class="order-card__divider"></div>` +
      `<section class="order-card__items"><ul class="order-items">` +
      order.items.map(i => `<li><span class="qty">${i.qty}×</span><span class="name">${i.menu_item_name || ''}</span></li>`).join('') +
      `</ul>` +
      actionsHtml +
      `</section>`;
    if (order.notes) {
      const notesValue = el.querySelector('.order-notes__value');
      if (notesValue) {
        notesValue.textContent = order.notes;
      }
    }
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
  if (completed) {
    completed.addEventListener('click', e => {
      const btn = e.target.closest('button.reorder-order');
      if (!btn) {
        return;
      }
      if (btn.disabled) {
        return;
      }
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Reordering…';
      fetch(`/orders/${btn.dataset.orderId}/reorder`, {
        method: 'POST',
        headers: { Accept: 'application/json' }
      })
        .then(res => {
          if (!res.ok) {
            return res
              .json()
              .catch(() => ({}))
              .then(data => Promise.reject({ status: res.status, ...data }));
          }
          return res.json().catch(() => ({}));
        })
        .then(data => {
          const redirect = data.redirect || '/cart';
          window.location.href = redirect;
        })
        .catch(err => {
          btn.disabled = false;
          btn.textContent = originalText;
          let message = 'Unable to reorder this order right now.';
          if (err && err.error === 'items_unavailable') {
            message = 'Some items are no longer available for reorder.';
          }
          alert(message);
        });
    });
  }
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
