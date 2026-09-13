(() => {
  const headerState=()=>document.body.classList.toggle('header-scrolled',scrollY>80);
  addEventListener('scroll',headerState,{passive:true});headerState();
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const progress = document.querySelector('.scrollprog');
  if (progress) {
    let frame = 0;
    const paint = () => { frame = 0; const available = document.documentElement.scrollHeight-innerHeight; progress.style.transform=`scaleX(${available>0?Math.min(1,Math.max(0,scrollY/available)):0})`; };
    const request = () => { if (!frame) frame=requestAnimationFrame(paint); };
    addEventListener('scroll',request,{passive:true}); addEventListener('resize',request,{passive:true});
    if ('ResizeObserver' in window) new ResizeObserver(request).observe(document.body);
    request();
  }
  document.querySelectorAll('[data-year]').forEach(e=>e.textContent=new Date().getFullYear());
  document.querySelectorAll('[data-strip]').forEach(root=>{
    const track=root.querySelector('.js-track'), first=root.querySelector('[data-dir-first]'), last=root.querySelector('[data-dir-last]');
    if (!track||!first||!last) return;
    const update=()=>{ const frame=track.getBoundingClientRect(); const visible=[...track.children].map((e,i)=>({i,r:e.getBoundingClientRect()})).filter(({r})=>r.right>frame.left+8&&r.left<frame.right-8); if(visible.length){first.textContent=String(visible[0].i+1).padStart(2,'0');last.textContent=String(visible.at(-1).i+1).padStart(2,'0');}};
    track.addEventListener('scroll',update,{passive:true}); addEventListener('resize',update,{passive:true}); update();
  });
  document.querySelectorAll('[data-clinic-carousel]').forEach(root=>{
    const viewport=root.querySelector('.clinic-carousel__viewport'), pairs=[...viewport.children], count=root.querySelector('[data-clinic-count]'); let index=0;
    const go=offset=>viewport.scrollTo({left:((index+offset+pairs.length)%pairs.length)*viewport.clientWidth,behavior:reduce?'auto':'smooth'});
    root.querySelector('[data-clinic-prev]').addEventListener('click',()=>go(-1)); root.querySelector('[data-clinic-next]').addEventListener('click',()=>go(1));
    viewport.addEventListener('scroll',()=>{index=Math.round(viewport.scrollLeft/viewport.clientWidth);count.textContent=String(index+1).padStart(2,'0')+' / '+String(pairs.length).padStart(2,'0');},{passive:true});
    viewport.addEventListener('keydown',e=>{if(e.target!==viewport)return;if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();go(e.key==='ArrowRight'?1:-1);}});
    addEventListener('resize',()=>viewport.scrollTo({left:index*viewport.clientWidth,behavior:'instant'}),{passive:true});
  });
  const lb=document.querySelector('.lightbox'); let trigger;
  if(lb){
    document.querySelectorAll('[data-lightbox]').forEach(e=>e.addEventListener('click',()=>{trigger=e;lb.setAttribute('aria-hidden','false');lb.querySelector('button')?.focus();}));
    const close=()=>{lb.setAttribute('aria-hidden','true');trigger?.focus();};
    lb.querySelector('button')?.addEventListener('click',close); lb.addEventListener('click',e=>{if(e.target===lb)close();});
    lb.addEventListener('keydown',e=>{if(e.key==='Tab'){e.preventDefault();lb.querySelector('button')?.focus();}}); addEventListener('keydown',e=>{if(e.key==='Escape')close();});
  }
  if(reduce||!('IntersectionObserver' in window))return;
  const observer=new IntersectionObserver(entries=>entries.forEach(({target,isIntersecting})=>{if(isIntersecting){target.classList.add('directions-visible');observer.unobserve(target);}}),{threshold:.12,rootMargin:'0px 0px -40px 0px'});
  document.querySelectorAll('.dirs__heading,.dirs .head__lead,.dirs__controls > .link,.dirs__cabinet,.dirs__story,.dirs .proc').forEach(e=>{if(!e.getClientRects().length)return;e.classList.add('directions-reveal');observer.observe(e);});
  const benefits=document.querySelector('.hero__facts');
  if(benefits){const io=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){benefits.classList.add('benefits-entered');io.disconnect();}},{threshold:.2});io.observe(benefits);}
  const motion=new IntersectionObserver(entries=>entries.forEach(({target,isIntersecting})=>{if(isIntersecting){target.classList.add('is-visible');motion.unobserve(target);}}),{threshold:.08});
  document.querySelectorAll('main .head:not(.dirs__head),.why__grid > *,.consult__list li,.rev-band,.faq__grid > div,.foot__grid > div').forEach((e,i)=>{if(e.getBoundingClientRect().top<innerHeight)return;e.classList.add('motion-reveal');e.style.setProperty('--motion-delay',`${i%3*70}ms`);motion.observe(e);});
})();
