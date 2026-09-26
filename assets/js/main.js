---
# يعالجه Jekyll لإضافة خريطة الروابط القديمة
---
(function(){
  /* old one-page links (/#about, /#act-2026-05-31 …) → new pages */
  var legacy={
    {%- for item in site.data.nav %}{% unless item.id == "home" %}
    {{ item.id | jsonify }}:{{ item.url | relative_url | jsonify }},
    {%- endunless %}{% endfor %}
    {%- assign items = site.activities | concat: site.news %}
    {%- for d in items %}{% if d.legacy_id %}
    {{ d.legacy_id | jsonify }}:{{ d.url | relative_url | jsonify }},
    {%- endif %}{% endfor %}
    "home":{{ "/" | relative_url | jsonify }}
  };
  var root={{ "/" | relative_url | jsonify }};
  if(location.pathname===root&&location.hash){
    var target=legacy[decodeURIComponent(location.hash.slice(1))];
    if(target&&target!==root){location.replace(target);return;}
  }

  /* mobile menu */
  var nav=document.getElementById('main-nav');
  var btn=document.querySelector('.menu-btn');
  if(btn&&nav){
    btn.addEventListener('click',function(){
      var open=nav.classList.toggle('open');
      btn.setAttribute('aria-expanded',open?'true':'false');
    });
    document.addEventListener('keydown',function(e){
      if(e.key==='Escape'&&nav.classList.contains('open')){nav.classList.remove('open');btn.setAttribute('aria-expanded','false');btn.focus();}
    });
  }

  /* language tabs: Arabic by default, choice remembered */
  var blocks=[].slice.call(document.querySelectorAll('.bi'));
  function setLang(l){
    blocks.forEach(function(b){
      b.dataset.show=l;
      b.querySelectorAll('.tabs button').forEach(function(t){t.setAttribute('aria-selected',t.dataset.l===l?'true':'false');});
    });
    try{localStorage.setItem('tm-lang',l);}catch(e){}
  }
  document.addEventListener('click',function(e){
    var t=e.target.closest('.bi .tabs button');
    if(t)setLang(t.dataset.l);
  });
  try{var saved=localStorage.getItem('tm-lang');if(saved==='tz'||saved==='ar')setLang(saved);}catch(e){}

  /* lightbox */
  var lb=document.getElementById('lb');
  if(lb){
    var lbImg=lb.querySelector('img');
    document.addEventListener('click',function(e){
      var z=e.target.closest('.zoom');
      if(!z)return;
      var img=z.querySelector('img');
      lbImg.src=z.dataset.zoom||img.src;
      lbImg.alt=img?img.alt:'';
      if(lb.showModal)lb.showModal();else window.open(lbImg.src);
    });
    lb.querySelector('.close').addEventListener('click',function(){lb.close();});
    lb.addEventListener('click',function(e){if(e.target===lb||e.target===lbImg)lb.close();});
  }

  var y=document.getElementById('year');if(y)y.textContent=new Date().getFullYear();
})();
