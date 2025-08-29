document.addEventListener('DOMContentLoaded', function(){
  const desc = document.querySelector('.bar-description');
  if(desc){
    const btn = desc.querySelector('.toggle-desc');
    if(btn){
      btn.addEventListener('click', () => {
        const expanded = desc.classList.toggle('expanded');
        btn.textContent = expanded ? 'Mostra meno' : 'Mostra di più';
        btn.setAttribute('aria-expanded', expanded);
      });
    }
  }
  const hours = document.querySelector('.opening-hours');
  if(hours){
    const btn = hours.querySelector('.toggle-hours');
    const list = hours.querySelector('ul');
    const desktop = window.matchMedia('(min-width:768px)').matches;
    if(!desktop){
      list.hidden = true;
    } else {
      btn.setAttribute('aria-expanded','true');
    }
    btn.addEventListener('click', () => {
      const expanded = list.hidden;
      list.hidden = !expanded;
      btn.setAttribute('aria-expanded', expanded);
    });
  }
});
