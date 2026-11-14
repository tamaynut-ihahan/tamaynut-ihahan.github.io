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
    function closeNav(){nav.classList.remove('open');btn.setAttribute('aria-expanded','false');}
    document.addEventListener('keydown',function(e){
      if(e.key==='Escape'&&nav.classList.contains('open')){closeNav();btn.focus();}
    });
    /* a tap outside the open menu closes it */
    document.addEventListener('click',function(e){
      if(nav.classList.contains('open')&&!nav.contains(e.target)&&!btn.contains(e.target))closeNav();
    });
  }

  /* header gains depth once the page scrolls */
  var hd=document.querySelector('.site-header'),stuck=null;
  function onScroll(){
    var s=window.scrollY>4;
    if(s!==stuck){stuck=s;hd.classList.toggle('is-stuck',s);}
  }
  if(hd){onScroll();window.addEventListener('scroll',onScroll,{passive:true});}

  /* scroll reveal: only for elements still below the fold, so nothing on screen ever blinks */
  var still=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if('IntersectionObserver' in window&&!still){
    var sel='main .band .bh, .lead-text, .intro .more, .axes li, .cards .card, .faces-grid > *, .infobox, .news-list li, .join-grid > *, .two-col > *, .goal-list li, .principles li, .faces-list figure, .gallery button, .pager a, .ag-shelf li, .lcards > li, .year-h, .ab-sec-h, .brand-card, .tl-body, .tl-mark, .ab-axes-head .lead-text, .ab-axis-cards li, .ab-quote blockquote, .ab-join-grid > *, .gl-ch-head > *, .gl-goals li, .gl-pr-head, .gl-seals li, .gl-join-grid > *, .ha-head > *, .face-stack, .faces-text, .hj-grid > *, .sec-row .more';
    var vh=window.innerHeight;
    var els=[].slice.call(document.querySelectorAll(sel)).filter(function(el){return el.getBoundingClientRect().top>vh*.92;});
    var io=new IntersectionObserver(function(entries){
      var n=0;
      entries.forEach(function(en){
        if(!en.isIntersecting)return;
        var el=en.target;
        el.style.transitionDelay=Math.min(n++,5)*90+'ms';
        el.classList.add('in');
        io.unobserve(el);
        /* once settled, hand the element back to its own hover/transition styles */
        setTimeout(function(){el.classList.remove('rv','in');el.style.transitionDelay='';},1700);
      });
    },{rootMargin:'0px 0px -8% 0px'});
    els.forEach(function(el){el.classList.add('rv');io.observe(el);});
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

  /* lightbox: counter, caption, arrows, keys and swipe (right-to-left: the next image lies to the left) */
  var lb=document.getElementById('lb');
  var calm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(lb){
    var lbImg=lb.querySelector('img'),cap=lb.querySelector('.lb-cap'),count=lb.querySelector('.lb-count');
    var prev=lb.querySelector('.prev'),next=lb.querySelector('.next');
    var group=[],pos=0;
    function src(z){var img=z.querySelector('img');return z.dataset.zoom||(img&&img.src);}
    function show(i,dir){
      pos=(i+group.length)%group.length;
      var z=group[pos],img=z.querySelector('img');
      lbImg.src=src(z);
      lbImg.alt=img?img.alt:'';
      if(cap){cap.textContent=lbImg.alt;cap.hidden=!lbImg.alt;}
      if(count){count.textContent=group.length>1?(pos+1)+' / '+group.length:'';}
      /* warm up the neighbours so arrows feel instant */
      if(group.length>1){[pos+1,pos-1].forEach(function(k){var n=group[(k+group.length)%group.length];var im=new Image();im.src=src(n);});}
      if(dir&&!calm&&lbImg.animate){
        lbImg.animate([{opacity:0,transform:'translateX('+(dir>0?'-':'')+'40px)'},{opacity:1,transform:'none'}],{duration:320,easing:'cubic-bezier(.16,1,.3,1)'});
      }
    }
    document.addEventListener('click',function(e){
      var z=e.target.closest('.zoom');
      if(!z)return;
      var g=z.closest('[data-gallery]');
      group=g?[].slice.call(g.querySelectorAll('.zoom')):[z];
      show(group.indexOf(z));
      prev.hidden=next.hidden=group.length<2;
      if(lb.showModal)lb.showModal();else window.open(lbImg.src);
    });
    prev.addEventListener('click',function(){show(pos-1,-1);});
    next.addEventListener('click',function(){show(pos+1,1);});
    lb.addEventListener('keydown',function(e){
      if(group.length<2)return;
      if(e.key==='ArrowLeft'){e.preventDefault();show(pos+1,1);}
      else if(e.key==='ArrowRight'){e.preventDefault();show(pos-1,-1);}
    });
    var x0=null,y0=0;
    lb.addEventListener('touchstart',function(e){x0=e.touches[0].clientX;y0=e.touches[0].clientY;},{passive:true});
    lb.addEventListener('touchend',function(e){
      if(x0===null||group.length<2)return;
      var dx=e.changedTouches[0].clientX-x0,dy=e.changedTouches[0].clientY-y0;x0=null;
      if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy))show(dx>0?pos+1:pos-1,dx>0?1:-1);
    });
    lb.querySelector('.close').addEventListener('click',function(){lb.close();});
    lb.addEventListener('click',function(e){if(e.target===lb||e.target===lbImg||e.target.classList.contains('lb-fig'))lb.close();});
  }

  /* lists: year links filter in place (without JS they simply jump to the year) */
  var years=document.querySelector('.years');
  if(years){
    var links=[].slice.call(years.querySelectorAll('a[data-year]'));
    var groupsY=[].slice.call(document.querySelectorAll('.year-group'));
    function filter(y,push){
      links.forEach(function(a){if(a.dataset.year===y)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current');});
      groupsY.forEach(function(g){g.hidden=!!y&&g.id!=='y'+y;});
      if(push&&history.replaceState)history.replaceState(null,'',y?'#y'+y:location.pathname);
    }
    years.addEventListener('click',function(e){
      var a=e.target.closest('a[data-year]');
      if(!a)return;
      e.preventDefault();
      filter(a.getAttribute('aria-current')?'':a.dataset.year,true);
    });
    function fromHash(){var hy=location.hash.match(/^#y(\d{4})$/);if(hy&&document.getElementById('y'+hy[1]))filter(hy[1],false);}
    fromHash();window.addEventListener('hashchange',fromHash);
  }

  /* goals: the sticky chapter bar follows the reading position */
  var gnav=document.querySelector('.gl-nav');
  if(gnav&&'IntersectionObserver' in window){
    var glinks={};
    [].forEach.call(gnav.querySelectorAll('a[href^="#"]'),function(a){glinks[a.getAttribute('href').slice(1)]=a;});
    var gio=new IntersectionObserver(function(entries){
      entries.forEach(function(en){
        if(!en.isIntersecting)return;
        var a=glinks[en.target.id];if(!a)return;
        Object.keys(glinks).forEach(function(k){glinks[k].removeAttribute('aria-current');});
        a.setAttribute('aria-current','true');
        var ul=a.closest('ul'),ar=a.getBoundingClientRect(),ur=ul.getBoundingClientRect();if(ul.scrollWidth>ul.clientWidth&&ul.scrollBy)ul.scrollBy({left:(ar.left+ar.width/2)-(ur.left+ur.width/2),behavior:'smooth'});
      });
    },{rootMargin:'-35% 0px -60% 0px'});
    Object.keys(glinks).forEach(function(id){var el=document.getElementById(id);if(el)gio.observe(el);});
  }

  var y=document.getElementById('year');if(y)y.textContent=new Date().getFullYear();
})();
