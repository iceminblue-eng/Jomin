(function(){
  var K='gwanrijaron-book', store={};
  try{ store=JSON.parse(localStorage.getItem(K)||'{}')||{} }catch(e){}
  function save(){ try{ localStorage.setItem(K,JSON.stringify(store)) }catch(e){} }

  document.querySelectorAll('input.fill').forEach(function(el){
    var k=el.dataset.k; if(store[k]) el.value=store[k];
    el.addEventListener('input',function(){ store[k]=el.value; save(); });
  });
  document.querySelectorAll('input.tick').forEach(function(el){
    var k=el.dataset.k; if(store[k]) el.checked=true;
    el.addEventListener('change',function(){ store[k]=el.checked||''; save(); });
  });

  var chaps=[].slice.call(document.querySelectorAll('.chap'));
  var tabs=[].slice.call(document.querySelectorAll('.tab'));
  function go(id,push){
    var hit=document.getElementById(id)||chaps[0];
    chaps.forEach(function(c){ c.hidden = c!==hit; });
    tabs.forEach(function(t){ t.classList.toggle('on', t.dataset.go===hit.id); });
    if(push!==false){ try{ history.replaceState(null,'','#'+hit.id) }catch(e){} }
    window.scrollTo(0,0); prog();
    var on=document.querySelector('.tab.on');
    if(on&&on.scrollIntoView) on.scrollIntoView({block:'nearest',inline:'center'});
  }
  tabs.forEach(function(t){ t.addEventListener('click',function(){ go(t.dataset.go) }) });

  var bar=document.getElementById('bar');
  function prog(){
    var h=document.documentElement.scrollHeight-window.innerHeight;
    bar.style.width=(h>0?Math.min(100,(window.scrollY/h)*100):0)+'%';
  }
  window.addEventListener('scroll',prog,{passive:true});
  window.addEventListener('resize',prog);
  go((location.hash||'').replace('#','')||chaps[0].id,false);
})();
