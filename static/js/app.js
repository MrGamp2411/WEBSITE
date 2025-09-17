document.addEventListener('DOMContentLoaded', function() {
  const APP_I18N = window.APP_I18N || {};
  const noticeTexts = (APP_I18N.notices && APP_I18N.notices.payment_failed) || {};
  const appTexts = APP_I18N.app || {};
  function formatTemplate(template, values){
    if(typeof template !== 'string') return '';
    return template.replace(/\{(\w+)\}/g, (_, key) => Object.prototype.hasOwnProperty.call(values, key) ? values[key] : '');
  }
  const FALLBACK_IMG = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCA0MDAgMjI1Jz48cmVjdCB3aWR0aD0nNDAwJyBoZWlnaHQ9JzIyNScgZmlsbD0nJTIzZjFmM2Y1Jy8+PC9zdmc+";
  const nav = document.querySelector('.site-header');
  if (nav) {
    const onScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  const searchInput = document.getElementById('barSearch') || document.getElementById('barSearchDesktop');
  const barCards = () => document.querySelectorAll('.bar-card, .bar-detail');
  const locationInput = document.getElementById('locationInput') || document.getElementById('locationInputDesktop');
  const suggestionsBox = document.getElementById('searchSuggestions') || document.getElementById('searchSuggestionsDesktop');
  const locationSelectors = document.querySelectorAll('.location-selector');
  const pausePopup = document.getElementById('servicePaused');
  const closePause = document.querySelector('.js-close-service-paused');
  function showPausePopup(){ if(pausePopup) pausePopup.hidden=false; }
  if(closePause){ closePause.addEventListener('click',()=>{ if(pausePopup) pausePopup.hidden=true; }); }
  if(window.orderingPaused && window.showServicePausedOnLoad){ showPausePopup(); }

  const params = new URLSearchParams(window.location.search);
  const notice = params.get('notice');
  if (['topup_failed', 'payment_failed'].includes(notice)) {
    const title = params.get('noticeTitle') || noticeTexts.title || 'Payment failed';
    const body = params.get('noticeBody') || noticeTexts.body || 'Payment was not successful. Please try again or contact our staff if the problem persists.';
    const closeLabel = noticeTexts.close || 'Close';
    const blocker = document.createElement('div');
    blocker.className = 'cart-blocker';
    const popup = document.createElement('div');
    popup.className = 'cart-popup';
    popup.innerHTML = `<p><strong>${title}</strong></p><p>${body}</p><div class="cart-popup-actions"><button type="button" class="btn btn--primary notice-close">${closeLabel}</button></div>`;
    blocker.appendChild(popup);
    document.body.appendChild(blocker);
    blocker.querySelector('.notice-close').addEventListener('click', () => blocker.remove());
    const url = new URL(window.location.href);
    ['notice','noticeTitle','noticeBody','noticeType'].forEach(k => url.searchParams.delete(k));
    window.history.replaceState({}, document.title, url.toString());
  }

  if (locationSelectors.length && locationInput) {
    locationSelectors.forEach(sel => {
      sel.addEventListener('click', () => {
        locationInput.value = '';
        locationInput.focus();
        locationInput.dispatchEvent(new Event('input'));
      });
    });
  }

  const locationPill = document.querySelector('.location-pill');
  if (locationPill && locationInput) {
    const updatePill = () => { locationPill.textContent = `📍 ${locationInput.value}`; };
    updatePill();
    ['input','change'].forEach(evt => locationInput.addEventListener(evt, updatePill));
    setTimeout(updatePill, 1000);
  }

  function toNumber(v){ if(v==null) return null; if(typeof v==='number') return Number.isFinite(v)?v:null; const m=String(v).replace(',', '.').match(/-?\d+(\.\d+)?/); return m?parseFloat(m[0]):null; }
  function toKm(v){ if(v==null) return null; if(typeof v==='number') return v>=1000? v/1000 : v; const n=toNumber(v); return n; }
  function renderMeta(el, data){
    const rating = toNumber(data.rating);
    const km = toKm(data.distance_km);
    const rEl = el.querySelector('.bar-rating');
    const dEl = el.querySelector('.bar-distance');
    if(rEl){
      if(rating!=null){
        rEl.innerHTML = '<i class="bi bi-star-fill" aria-hidden="true"></i> <span class="rating-value">'+rating.toFixed(1)+'</span>';
        rEl.hidden = false;
        rEl.dataset.hasRating = 'true';
      } else {
        rEl.hidden = true;
        rEl.dataset.hasRating = 'false';
      }
    }
    if(dEl){
      if(km!=null){
        dEl.innerHTML = '<i class="bi bi-geo-alt-fill" aria-hidden="true"></i> <span class="distance-value">'+km.toFixed(1)+' km</span>';
        dEl.hidden = false;
        dEl.dataset.hasDistance = 'true';
      } else {
        dEl.hidden = true;
        dEl.dataset.hasDistance = 'false';
      }
    }
  }

  barCards().forEach(card => renderMeta(card, card.dataset));

  function debounce(fn, delay=300){let t;return (...args)=>{clearTimeout(t);t=setTimeout(()=>fn.apply(this,args),delay);};}

  function filterBars(term) {
    const t = term.toLowerCase();
    barCards().forEach(card => {
      const {name='', address='', city='', state=''} = card.dataset;
      card.style.display = (name.includes(t) || address.includes(t) || city.includes(t) || state.includes(t)) ? '' : 'none';
    });
  }

  function renderSuggestions(bars) {
    if (!suggestionsBox) return;
    if (!bars.length) {
      suggestionsBox.innerHTML = '';
      suggestionsBox.classList.remove('show');
      return;
    }
    const items = bars.map(bar => `
      <li data-bar-id="${bar.id}">
        <a class="bar-card" href="/bars/${bar.id}" aria-label="${formatTemplate(appTexts.open_label, { bar: bar.name }) || `Open ${bar.name}`}">
          <div class="thumb-wrapper"><img class="thumb" src="${bar.photo_url || FALLBACK_IMG}" alt="${bar.name} photo" loading="lazy" decoding="async" width="400" height="225" srcset="${bar.photo_url || FALLBACK_IMG} 400w, ${bar.photo_url || FALLBACK_IMG} 800w" sizes="(max-width: 600px) 100vw, 400px" onerror="this.src='${FALLBACK_IMG}';this.onerror=null;"></div>
          <h3 class="title">${bar.name}</h3>
          <div class="bar-meta">
            <span class="bar-rating" data-has-rating="true" hidden></span>
            <span class="bar-distance" data-has-distance="true" hidden></span>
          </div>
          <address>${bar.address}, ${bar.city}, ${bar.state}</address>
          <p class="desc">${bar.description}</p>
        </a>
      </li>
    `).join('');
    suggestionsBox.innerHTML = `<ul class="bars">${items}</ul>`;
    suggestionsBox.classList.add('show');
    suggestionsBox.querySelectorAll('.bar-card').forEach((card, i) => {
      renderMeta(card, bars[i] || {});
    });
  }

  function fetchSuggestions(term) {
    if (!suggestionsBox) return;
    const q = term.trim();
    if (!q) {
      suggestionsBox.innerHTML = '';
      suggestionsBox.classList.remove('show');
      return;
    }
    fetch(`/api/search?q=${encodeURIComponent(q)}`)
      .then(res => res.json())
      .then(data => renderSuggestions(data.bars.slice(0,5)));
  }

  if (searchInput) {
    searchInput.addEventListener('focus', () => {
      searchInput.classList.add('expanded');
    });
    const handleInput = debounce(() => {
      filterBars(searchInput.value);
      fetchSuggestions(searchInput.value);
    }, 300);
    searchInput.addEventListener('input', handleInput);
    searchInput.addEventListener('blur', () => {
      setTimeout(() => {
        if (searchInput.value.trim() === '') {
          searchInput.classList.remove('expanded');
        }
        if (suggestionsBox) suggestionsBox.classList.remove('show');
      }, 100);
    });
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        window.location.href = `/search?q=${encodeURIComponent(searchInput.value)}`;
      }
    });
  }

  if (suggestionsBox) {
    suggestionsBox.addEventListener('click', (e) => {
      const li = e.target.closest('li[data-bar-id]');
      if (li) {
        const id = li.getAttribute('data-bar-id');
        window.location.href = `/bars/${id}`;
      }
    });
  }

  const allBarItems = barCards();

  function sortBarsByDistance(){
    const list = document.getElementById('barList');
    if(!list) return;
    const items = Array.from(list.children);
    const browse = list.querySelector('.browse-bars-card')?.closest('li');
    const sortable = browse ? items.filter(it => it !== browse) : items;
    sortable.sort((a,b)=>{
      const da = parseFloat(a.querySelector('.bar-card').dataset.distance_km || 'Infinity');
      const db = parseFloat(b.querySelector('.bar-card').dataset.distance_km || 'Infinity');
      return da - db;
    });
    sortable.forEach(it=>list.appendChild(it));
    if (browse) list.appendChild(browse);
    list.scrollLeft = 0;
  }

  function showNearestOpenBars(){
    const list = document.getElementById('barList');
    if(!list) return;
    const items = Array.from(list.children);
    let shown = 0;
    let anyOpen = false;
    items.forEach(li => {
      const card = li.querySelector('.bar-card');
      const o = card.dataset.open;
      if (o === undefined) {
        li.hidden = false;
        return;
      }
      const open = o === 'true';
      if (open && shown < 5) {
        li.hidden = false;
        shown++;
        anyOpen = true;
      } else {
        li.hidden = true;
      }
    });
    const msg = document.getElementById('noBarsMessage');
    if (msg) msg.hidden = anyOpen;
  }

  function updateDistances(uLat, uLon) {
    allBarItems.forEach(item => {
      const bLat = parseFloat(item.dataset.latitude);
      const bLon = parseFloat(item.dataset.longitude);
      if (!isFinite(bLat) || !isFinite(bLon)) return;
      const dist = haversine(uLat, uLon, bLat, bLon);
      item.dataset.distance_km = dist;
      renderMeta(item, { rating: item.dataset.rating, distance_km: dist });
    });
    sortBarsByDistance();
    showNearestOpenBars();
  }

  function reverseGeocode(lat, lon) {
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`)
      .then(res => res.json())
      .then(data => {
        if (!locationInput) return;
        if (data.address) {
          const {city, town, village, postcode} = data.address;
          const place = city || town || village;
          if (place) {
            locationInput.value = postcode ? `${place} ${postcode}` : place;
            return;
          }
        }
        locationInput.value = data.display_name || `${lat.toFixed(3)}, ${lon.toFixed(3)}`;
      })
      .catch(() => {
        if (locationInput) locationInput.value = `${lat.toFixed(3)}, ${lon.toFixed(3)}`;
      });
  }

  function setLocation(lat, lon, label) {
    updateDistances(lat, lon);
    if (locationInput) {
      locationInput.value = label || `${lat.toFixed(3)}, ${lon.toFixed(3)}`;
    }
    reverseGeocode(lat, lon);
  }

  if (allBarItems.length) {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(pos => {
        const {latitude, longitude} = pos.coords;
        setLocation(latitude, longitude);
      });
    }

    sortBarsByDistance();
    showNearestOpenBars();

    function geocodeAndSet(city) {
      fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(city)}`)
        .then(res => res.json())
        .then(data => {
          if (data && data.length) {
            const {lat, lon} = data[0];
            setLocation(parseFloat(lat), parseFloat(lon), city);
          }
        });
    }

    if (locationInput) {
      locationInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const city = locationInput.value.trim();
          if (city) geocodeAndSet(city);
        }
      });
    }
  }

  function haversine(lat1, lon1, lat2, lon2) {
    const toRad = deg => deg * Math.PI / 180;
    const R = 6371;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  const toggle = document.getElementById('themeToggle');
  if (toggle) {
    const applyTheme = (mode) => {
      document.body.classList.toggle('dark-mode', mode === 'dark');
      toggle.textContent = mode === 'dark' ? '☀️' : '🌙';
      toggle.setAttribute('aria-label', mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    };
    toggle.addEventListener('click', () => {
      const mode = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
      applyTheme(mode);
      localStorage.setItem('theme', mode);
    });
    const stored = localStorage.getItem('theme') || 'light';
    applyTheme(stored);
  }

  const menuToggles = document.querySelectorAll('.js-open-menu');
  const mobileMenu = document.getElementById('mobileMenu');
  let backdrop;

  function ensureMenuBackdrop() {
    if (backdrop && document.body.contains(backdrop)) {
      return backdrop;
    }

    backdrop = null;
    for (const el of document.querySelectorAll('.menu-backdrop')) {
      if (!el.classList.contains('language-backdrop')) {
        backdrop = el;
        break;
      }
    }

    if (!backdrop && mobileMenu) {
      backdrop = document.createElement('div');
      backdrop.className = 'menu-backdrop';
      backdrop.hidden = true;
      mobileMenu.insertAdjacentElement('afterend', backdrop);
    }

    return backdrop;
  }

  ensureMenuBackdrop();
  const closeBtn = mobileMenu?.querySelector('.js-close-menu');
  const contentEls = document.querySelectorAll('main, .hdr-sub, footer');
  let activeToggle;
  let lastFocused;

  const handleKeydown = (e) => { if (e.key === 'Escape') closeMenu(); };

  function openMenu(btn) {
    const overlay = ensureMenuBackdrop();
    if (!mobileMenu || !overlay) return;
    activeToggle = btn;
    lastFocused = document.activeElement;
    activeToggle.setAttribute('aria-expanded', 'true');
    mobileMenu.hidden = false;
    overlay.hidden = false;
    requestAnimationFrame(() => {
      mobileMenu.classList.add('is-open');
      overlay.classList.add('is-open');
    });
    document.body.style.overflow = 'hidden';
    contentEls.forEach(el => el.setAttribute('aria-hidden','true'));
    document.addEventListener('keydown', handleKeydown);
    overlay.addEventListener('click', closeMenu);
    closeBtn?.addEventListener('click', closeMenu);
    const firstItem = mobileMenu.querySelector('[role="menuitem"]');
    firstItem && firstItem.focus();
  }

  function closeMenu() {
    const overlay = ensureMenuBackdrop();
    if (!mobileMenu || !overlay) return;
    activeToggle && activeToggle.setAttribute('aria-expanded', 'false');
    mobileMenu.classList.remove('is-open');
    overlay.classList.remove('is-open');
    document.body.style.overflow = '';
    mobileMenu.hidden = true;
    overlay.hidden = true;
    contentEls.forEach(el => el.removeAttribute('aria-hidden'));
    document.removeEventListener('keydown', handleKeydown);
    overlay.removeEventListener('click', closeMenu);
    closeBtn?.removeEventListener('click', closeMenu);
    lastFocused && lastFocused.focus();
  }

  menuToggles.forEach(btn => {
    btn.addEventListener('click', () => {
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      expanded ? closeMenu() : openMenu(btn);
    });
  });

  mobileMenu?.addEventListener('click', (e) => {
    const item = e.target.closest('[role="menuitem"]');
    if (item && !item.hasAttribute('data-keep-menu-open')) {
      closeMenu();
    }
  });

  mobileMenu?.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    const items = mobileMenu.querySelectorAll('[role="menuitem"], .js-close-menu');
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  const languageDialog = document.getElementById('languageDialog');
  const languageBackdrop = document.querySelector('.language-backdrop');
  const languageTrigger = document.querySelector('.js-open-language');
  const languageClose = languageDialog?.querySelector('.js-close-language');
  const languageOptions = languageDialog?.querySelectorAll('.language-option');
  let languageLastFocused;

  const handleLanguageKeydown = (event) => {
    if (!languageDialog || languageDialog.hidden) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeLanguageDialog();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = languageDialog.querySelectorAll('.language-dialog__close, .language-option');
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  function openLanguageDialog() {
    if (!languageDialog || !languageBackdrop) return;
    languageLastFocused = document.activeElement;
    languageDialog.hidden = false;
    languageBackdrop.hidden = false;
    requestAnimationFrame(() => {
      languageDialog.classList.add('is-open');
      languageBackdrop.classList.add('is-open');
    });
    document.body.style.overflow = 'hidden';
    contentEls.forEach(el => el.setAttribute('aria-hidden', 'true'));
    document.addEventListener('keydown', handleLanguageKeydown);
    languageBackdrop.removeEventListener('click', closeLanguageDialog);
    languageBackdrop.addEventListener('click', closeLanguageDialog);
    if (languageClose) {
      languageClose.removeEventListener('click', closeLanguageDialog);
      languageClose.addEventListener('click', closeLanguageDialog);
    }
    const activeOption = languageDialog.querySelector('.language-option[aria-checked="true"]') || languageDialog.querySelector('.language-option');
    activeOption?.focus();
  }

  function closeLanguageDialog() {
    if (!languageDialog || !languageBackdrop) return;
    languageDialog.classList.remove('is-open');
    languageBackdrop.classList.remove('is-open');
    setTimeout(() => {
      languageDialog.hidden = true;
      languageBackdrop.hidden = true;
    }, 220);
    if (!mobileMenu?.classList.contains('is-open')) {
      document.body.style.overflow = '';
      contentEls.forEach(el => el.removeAttribute('aria-hidden'));
    }
    document.removeEventListener('keydown', handleLanguageKeydown);
    languageBackdrop.removeEventListener('click', closeLanguageDialog);
    languageClose?.removeEventListener('click', closeLanguageDialog);
    languageLastFocused && languageLastFocused.focus();
  }

  function setLanguage(code) {
    if (!code) return;
    const url = new URL(window.location.href);
    url.searchParams.set('lang', code);
    window.location.href = url.toString();
  }

  languageTrigger?.addEventListener('click', (event) => {
    event.preventDefault();
    closeMenu();
    openLanguageDialog();
  });

  languageOptions?.forEach((btn) => {
    btn.addEventListener('click', () => {
      setLanguage(btn.getAttribute('data-lang'));
    });
  });

  document.querySelector('.js-open-search')?.addEventListener('click', () => {
    const ov = document.querySelector('.search-overlay');
    ov?.classList.add('open');
    ov?.removeAttribute('hidden');
  });
  document.querySelector('.overlay-close')?.addEventListener('click', () => {
    const ov = document.querySelector('.search-overlay');
    ov?.classList.remove('open');
    ov?.setAttribute('hidden','');
  });

  // Carousel controls
  function setupCarousels(){
    document.querySelectorAll('.bar-section,.product-section').forEach(section=>{
      const scroller=section.querySelector('.scroller');
      const prev=section.querySelector('.scroll-btn.prev');
      const next=section.querySelector('.scroll-btn.next');
      if(!scroller) return;
      const getWidth=()=>{const card=scroller.querySelector('li:not([hidden]) .bar-card,li:not([hidden]) .product-card');if(!card) return 0;const style=getComputedStyle(card);return card.offsetWidth+parseFloat(style.marginRight)+parseFloat(style.marginLeft);};
      let w=getWidth();
      const scrollBy=dir=>scroller.scrollBy({left:dir*w,behavior:'smooth'});
      prev?.addEventListener('click',()=>scrollBy(-1));
      next?.addEventListener('click',()=>scrollBy(1));
      window.addEventListener('resize',()=>{w=getWidth();});
      scroller.addEventListener('keydown',e=>{if(e.key==='ArrowRight'){e.preventDefault();scrollBy(1);}if(e.key==='ArrowLeft'){e.preventDefault();scrollBy(-1);}});
    });
  }
  setupCarousels();

  function updateMiniCart(json){
    const badge=document.querySelector('.cart-badge');
    if(badge&&typeof json.count==="number") badge.textContent=json.count;
    const totalEl=document.querySelector('.mini-cart-total');
    if(totalEl&&json.totalFormatted) totalEl.textContent=json.totalFormatted;
    const list=document.querySelector('.mini-cart-items');
    if(list&&Array.isArray(json.items)){
      list.innerHTML=json.items.map(i=>`<li>${i.qty}× ${i.name} - ${i.lineTotal}</li>`).join('');
    }
  }

  function showQuantityControls(form,qty){
    const product=form.querySelector('input[name="product_id"]');
    const controls=document.createElement('div');
    controls.className='qty-controls';
    controls.innerHTML=`<button type="button" class="btn btn--primary btn--small qty-minus" aria-label="Decrease quantity">-</button><span class="qty-display">${qty}</span><button type="button" class="btn btn--primary btn--small qty-plus" aria-label="Increase quantity">+</button>`;
    form.innerHTML='';
    if(product) form.append(product);
    form.append(controls);
  }

  async function hydrateQuantityControls(){
    const forms=document.querySelectorAll('.add-to-cart-form');
    if(!forms.length) return;
    try{
      const res=await fetch('/cart',{headers:{Accept:'application/json'}});
      if(!res.ok) return;
      const json=await res.json();
      updateMiniCart(json);
      forms.forEach(f=>{
        const id=f.querySelector('input[name="product_id"]')?.value;
        const item=json.items?.find(i=>i.id===Number(id));
        if(item) showQuantityControls(f,item.qty);
      });
    }catch(err){
      console.error('Cart fetch failed',err);
    }
  }
  hydrateQuantityControls();

  // Add to cart without page reload
  document.addEventListener('submit',async e=>{
    if(!e.target.matches('.add-to-cart-form')) return;
    const form=e.target;
    e.preventDefault();
    if(window.orderingPaused){ showPausePopup(); return; }
    const btn=form.querySelector('button[type="submit"]');
    if(btn?.disabled) return;
    const data=new URLSearchParams(new FormData(form));
    btn.disabled=true;
    const original=btn.textContent;
    btn.textContent='Adding…';
    try{
      const res=await fetch(form.action,{method:'POST',body=data,headers:{Accept:'application/json'}});
      if(res.status===409){ window.orderingPaused=true; showPausePopup(); return; }
      if(!res.ok) throw new Error();
      const json=await res.json();
      updateMiniCart(json);
      const id=data.get('product_id');
      const item=json.items?.find(i=>i.id===Number(id));
      showQuantityControls(form,item?item.qty:1);
    }catch(err){
      alert('Failed to add to cart');
    }finally{
      btn.disabled=false;
      btn.textContent=original;
    }
  });

  document.addEventListener('click',async e=>{
    const btn=e.target.closest('.qty-plus,.qty-minus');
    if(!btn) return;
    const form=btn.closest('.add-to-cart-form');
    if(!form) return;
    e.preventDefault();
    const productInput=form.querySelector('input[name="product_id"]');
    const display=form.querySelector('.qty-display');
    if(!productInput||!display) return;
    let qty=parseInt(display.textContent,10)||0;
    if(btn.matches('.qty-plus') && window.orderingPaused){ showPausePopup(); return; }
    btn.disabled=true;
    try{
      if(btn.matches('.qty-plus')){
        const data=new URLSearchParams({product_id:productInput.value});
        const res=await fetch(form.action,{method:'POST',body:data,headers:{Accept:'application/json'}});
        if(res.status===409){ window.orderingPaused=true; showPausePopup(); return; }
        if(!res.ok) throw new Error();
        const json=await res.json();
        updateMiniCart(json);
        const item=json.items?.find(i=>i.id===Number(productInput.value));
        qty=item?item.qty:qty+1;
        display.textContent=qty;
      }else{
        qty-=1;
        const data=new URLSearchParams({product_id:productInput.value,quantity:qty});
        const res=await fetch('/cart/update',{method:'POST',body:data,headers:{Accept:'application/json'}});
        if(!res.ok) throw new Error();
        const json=await res.json();
        updateMiniCart(json);
        if(qty<=0){
          form.innerHTML='';
          form.append(productInput);
          const add=document.createElement('button');
          add.className='btn btn--primary btn--small add-to-cart';
          add.type='submit';
          add.textContent='Add to Cart';
          form.append(add);
        }else{
          display.textContent=qty;
        }
      }
    }catch(err){
      alert('Cart update failed');
    }finally{
      btn.disabled=false;
    }
  });

  const clearBtn=document.querySelector('.js-clear-cart');
  if(clearBtn){
    clearBtn.addEventListener('click',async()=>{
      clearBtn.disabled=true;
      try{
        await fetch('/cart/clear',{method:'POST',headers:{Accept:'application/json'}});
        location.reload();
      }catch(err){
        alert('Failed to clear cart');
        clearBtn.disabled=false;
      }
    });
  }

});
