function toNumber(v){
  if(v==null) return null;
  if(typeof v==='number') return Number.isFinite(v)?v:null;
  const m=String(v).replace(',','.').match(/-?\d+(\.\d+)?/);
  return m?parseFloat(m[0]):null;
}

const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();

function debounce(fn,delay){
  let t;return(...args)=>{clearTimeout(t);t=setTimeout(()=>fn.apply(this,args),delay)};
}

function getActiveFilterCount(s){
  let c=0;
  if(s.q) c++;
  if(s.city) c++;
  if(s.dist_km!=null) c++;
  if(s.rating>0) c++;
  if(s.open_state!=='ANY') c++;
  if(s.categories.length) c++;
  return c;
}

function initFiltersUI(){
  const list=document.getElementById('allBarList');
  if(!list) return;
  const cards=Array.from(list.querySelectorAll('.bar-card'));

  const toggle=document.getElementById('filtersToggle');
  const panel=document.getElementById('filtersPanel');
  const overlay=document.getElementById('filtersOverlay');
  const form=document.getElementById('filtersForm');
  const badge=document.getElementById('filtersBadge');
  const summary=document.getElementById('filtersSummary');

  const nameInput=document.getElementById('filterName');
  const cityInput=document.getElementById('filterCity');
  const distanceInput=document.getElementById('filterDistance');
  const distanceValue=document.getElementById('distanceValue');
  const ratingInput=document.getElementById('filterRating');
  const ratingGroup=document.getElementById('ratingGroup');
  const openState=document.getElementById('openState');
  const categoriesWrap=document.getElementById('categoryChips');
  const applyBtn=document.getElementById('filtersApply');
  const resetBtn=document.getElementById('filtersReset');

  const defaults={q:'',city:'',dist_km:null,rating:0,open_state:'ANY',categories:[]};
  let state={...defaults};
  let draft={...defaults};
  let dirty=false;

  function readStateFromURL(){
    const params=new URLSearchParams(location.search);
    state={...defaults};
    if(params.get('q')) state.q=norm(params.get('q'));
    if(params.get('city')) state.city=norm(params.get('city'));
    if(params.get('dist_km')) state.dist_km=toNumber(params.get('dist_km'));
    if(params.get('rating')) state.rating=toNumber(params.get('rating'))||0;
    if(params.get('open_state')) state.open_state=params.get('open_state');
    if(params.get('categories')) state.categories=params.get('categories').split(',').map(norm).filter(Boolean);
    draft={...state};
  }

  function writeStateToURL(){
    const params=new URLSearchParams();
    if(state.q) params.set('q',state.q);
    if(state.city) params.set('city',state.city);
    if(state.dist_km!=null) params.set('dist_km',state.dist_km);
    if(state.rating>0) params.set('rating',state.rating);
    if(state.open_state!=='ANY') params.set('open_state',state.open_state);
    if(state.categories.length) params.set('categories',state.categories.join(','));
    const qs=params.toString();
    history.replaceState(null,'',qs?`?${qs}`:location.pathname);
  }

  function updateBadge(count){
    badge.textContent=count;
    badge.hidden=count===0;
  }

  function updateSummary(){
    const count=getActiveFilterCount(state);
    summary.innerHTML='';
    if(!count){summary.hidden=true;return;}
    const pills=[];
    if(state.city) pills.push(state.city);
    if(state.dist_km!=null) pills.push(`≤${state.dist_km} km`);
    if(state.rating>0) pills.push(`★≥${state.rating}`);
    if(state.open_state==='OPEN_NOW') pills.push('Aperti ora');
    if(state.open_state==='CLOSED') pills.push('Chiusi ora');
    if(state.categories.length) pills.push(`${state.categories.length} categorie`);
    pills.slice(0,3).forEach(p=>{
      const pill=document.createElement('span');
      pill.className='pill';
      pill.textContent=p;
      summary.appendChild(pill);
    });
    const reset=document.createElement('button');
    reset.type='button';
    reset.className='pill reset';
    reset.textContent='Reimposta';
    reset.addEventListener('click',()=>{resetBtn.click();summary.hidden=true;});
    summary.appendChild(reset);
    summary.hidden=false;
  }

  function openPanel(){
    panel.hidden=false;
    overlay.hidden=false;
    panel.removeAttribute('aria-hidden');
    toggle.setAttribute('aria-expanded','true');
    panel.classList.add('open');
    form.querySelector('input,select,button')?.focus();
  }

  function closePanel(){
    panel.hidden=true;
    overlay.hidden=true;
    panel.setAttribute('aria-hidden','true');
    toggle.setAttribute('aria-expanded','false');
    panel.classList.remove('open');
    toggle.focus();
  }

  toggle?.addEventListener('click',()=>{
    panel.hasAttribute('hidden')?openPanel():closePanel();
  });
  overlay?.addEventListener('click',closePanel);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hasAttribute('hidden')) closePanel();});

  function applyFilters(){
    cards.forEach(card=>{
      const data=card.dataset;let show=true;
      if(state.q && !norm(data.name).includes(state.q)) show=false;
      if(state.city && !norm(data.city).includes(state.city)) show=false;
      const km=toNumber(data.distance_km);
      if(state.dist_km!=null && (km==null || km>state.dist_km)) show=false;
      const rating=toNumber(data.rating);
      if(state.rating>0 && (rating==null || rating<state.rating)) show=false;
      if(state.open_state==='OPEN_NOW' && data.open!=='true') show=false;
      if(state.open_state==='CLOSED' && data.open!=='false') show=false;
      if(state.categories.length){
        const barCats=(data.categories||'').split(',').map(norm);
        if(!state.categories.some(c=>barCats.includes(c))) show=false;
      }
      card.closest('li').hidden=!show;
    });
    const count=getActiveFilterCount(state);
    updateBadge(count);
    updateSummary();
    writeStateToURL();
  }

  function markDirty(){
    dirty=true;
    applyBtn.disabled=false;
    updateBadge(getActiveFilterCount(draft));
  }

  nameInput?.addEventListener('input',debounce(e=>{
    draft.q=norm(e.target.value);
    const btn=form.querySelector('.clear-input[data-target="filterName"]');
    if(btn) btn.hidden=!e.target.value;
    markDirty();
  },300));

  cityInput?.addEventListener('input',e=>{
    draft.city=norm(e.target.value);
    const btn=form.querySelector('.clear-input[data-target="filterCity"]');
    if(btn) btn.hidden=!e.target.value;
    markDirty();
  });

  distanceInput?.addEventListener('input',e=>{
    distanceValue.textContent=e.target.value+' km';
    draft.dist_km=toNumber(e.target.value);
    markDirty();
  });

  if(ratingGroup && ratingInput){
    for(let i=0;i<=5;i++){
      const label=document.createElement('label');
      label.className='rating-option';
      const stars=i===0?'Qualsiasi':'<span class="stars">'+('★'.repeat(i))+'</span>';
      label.innerHTML=`<input type="radio" name="rating" value="${i}"${i===0?' checked':''}> ${stars}`;
      ratingGroup.appendChild(label);
    }
    ratingGroup.addEventListener('change',e=>{
      if(e.target.name==='rating'){
        draft.rating=toNumber(e.target.value)||0;
        ratingInput.value=draft.rating;
        markDirty();
      }
    });
  }

  openState?.addEventListener('change',e=>{
    if(e.target.name==='open_state'){
      draft.open_state=e.target.value;
      markDirty();
    }
  });

  if(categoriesWrap){
    const allCategories=[
      "Cocktail classico","Mixology&Signature","Enoteca/Vineria (Merlot)","Birreria artigianale","Pub/Irish pub",
      "Gastropub","Sports bar","Lounge bar","Rooftop/Sky bar","Speakeasy","Live music/Jazz bar","Piano bar",
      "Karaoke bar","Club/Discoteca bar","Aperitivo&Cicchetti","Caffetteria/Espresso bar","Pasticceria-bar",
      "Paninoteca/Snack bar","Gelateria-bar","Bar di paese","Lakefront/Lido (lago)","Grotto ticinese","Hotel bar",
      "Shisha/Hookah lounge","Cigar&Whisky lounge","Gin bar","Rum/Tiki bar","Tequila/Mezcalería",
      "Biliardo&Darts pub","Afterwork/Business bar"
    ];
    allCategories.forEach(c=>{
      const chip=document.createElement('button');
      chip.type='button';
      chip.className='chip';
      chip.dataset.value=norm(c);
      chip.textContent=c;
      categoriesWrap.appendChild(chip);
    });
    categoriesWrap.addEventListener('click',e=>{
      const chip=e.target.closest('.chip');
      if(!chip) return;
      const val=chip.dataset.value;
      if(chip.classList.toggle('active')){
        draft.categories.push(val);
      }else{
        draft.categories=draft.categories.filter(v=>v!==val);
      }
      markDirty();
    });
  }

  document.querySelectorAll('.clear-input').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const target=document.getElementById(btn.dataset.target);
      if(target){
        target.value='';
        if(target===nameInput) draft.q='';
        if(target===cityInput) draft.city='';
        btn.hidden=true;
        markDirty();
      }
    });
  });

  resetBtn?.addEventListener('click',()=>{
    draft={...defaults};
    state={...defaults};
    form.reset();
    ratingInput.value='0';
    distanceInput.value=distanceInput.max;
    distanceValue.textContent=distanceInput.value+' km';
    categoriesWrap?.querySelectorAll('.chip.active').forEach(c=>c.classList.remove('active'));
    applyFilters();
  });

  applyBtn?.addEventListener('click',()=>{
    applyBtn.disabled=true;
    applyBtn.querySelector('.spinner')?.removeAttribute('hidden');
    setTimeout(()=>{
      state={...draft};
      applyFilters();
      closePanel();
      applyBtn.querySelector('.spinner')?.setAttribute('hidden','');
      dirty=false;
    },100);
  });

  readStateFromURL();
  form.reset();
  nameInput.value=state.q||'';
  cityInput.value=state.city||'';
  if(state.q) form.querySelector('.clear-input[data-target="filterName"]').hidden=false;
  if(state.city) form.querySelector('.clear-input[data-target="filterCity"]').hidden=false;
  if(state.dist_km!=null){
    distanceInput.value=state.dist_km;
    distanceValue.textContent=state.dist_km+' km';
  }else{
    distanceInput.value=distanceInput.max;
    distanceValue.textContent=distanceInput.value+' km';
  }
  ratingInput.value=state.rating;
  const ratingRadio=ratingGroup.querySelector(`input[value="${state.rating}"]`);
  if(ratingRadio) ratingRadio.checked=true;
  openState.querySelector(`input[value="${state.open_state}"]`).checked=true;
  if(categoriesWrap){
    state.categories.forEach(v=>{
      const chip=categoriesWrap.querySelector(`.chip[data-value="${v}"]`);
      chip?.classList.add('active');
    });
  }
  updateBadge(getActiveFilterCount(state));
  updateSummary();
  applyFilters();
}

document.addEventListener('DOMContentLoaded',initFiltersUI);

