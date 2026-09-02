(() => {
  const body = document.body;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- мобильное меню ---- */
  const navBtn = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.nav');
  if (navBtn && nav) {
    const setMenu = (open) => {
      navBtn.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
      body.classList.toggle('menu-open', open);
    };
    navBtn.addEventListener('click', () => setMenu(!nav.classList.contains('is-open')));
    nav.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => setMenu(false)));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setMenu(false); });
  }

  /* ---- год в подвале ---- */
  document.querySelectorAll('[data-year]').forEach((n) => { n.textContent = new Date().getFullYear(); });

  /* ---- карусели фотографий ---- */
  document.querySelectorAll('[data-slider]').forEach((root) => {
    const track = root.querySelector('.wslider-track');
    const slides = [...track.children];
    const dotsWrap = root.querySelector('.wslider-dots');
    const prev = root.querySelector('.wslider-arrow.prev');
    const next = root.querySelector('.wslider-arrow.next');
    let i = 0;
    slides.forEach((_, n) => {
      const d = document.createElement('button');
      d.type = 'button';
      d.setAttribute('aria-label', 'Фото ' + (n + 1));
      if (n === 0) d.className = 'active';
      d.addEventListener('click', () => go(n));
      dotsWrap.appendChild(d);
    });
    const dots = [...dotsWrap.children];
    function go(n) {
      i = (n + slides.length) % slides.length;
      track.style.transform = 'translateX(-' + (i * 100) + '%)';
      dots.forEach((d, k) => d.classList.toggle('active', k === i));
    }
    prev?.addEventListener('click', () => go(i - 1));
    next?.addEventListener('click', () => go(i + 1));

    let sx = 0, sy = 0, drag = false, moved = false;
    track.addEventListener('pointerdown', (e) => { sx = e.clientX; sy = e.clientY; drag = true; moved = false; });
    track.addEventListener('pointermove', (e) => {
      if (drag && Math.abs(e.clientX - sx) > Math.abs(e.clientY - sy) && Math.abs(e.clientX - sx) > 6) moved = true;
    });
    track.addEventListener('pointerup', (e) => {
      if (!drag) return;
      drag = false;
      const dx = e.clientX - sx;
      if (moved && Math.abs(dx) > 40) go(i + (dx < 0 ? 1 : -1));
    });
    track.addEventListener('click', (e) => { if (moved) { e.preventDefault(); e.stopPropagation(); } }, true);
  });

  /* ---- горизонтальные ленты со стрелками (услуги, отзывы) ---- */
  document.querySelectorAll('[data-strip]').forEach((wrap) => {
    const track = wrap.querySelector('.js-track');
    if (!track) return;
    const step = () => {
      const c = track.firstElementChild;
      return c ? (c.getBoundingClientRect().width + 16) * (wrap.dataset.strip === 'wide' ? 1 : 2) : 300;
    };
    wrap.querySelectorAll('[data-prev]').forEach((b) => b.addEventListener('click', () => track.scrollBy({ left: -step(), behavior: 'smooth' })));
    wrap.querySelectorAll('[data-next]').forEach((b) => b.addEventListener('click', () => track.scrollBy({ left: step(), behavior: 'smooth' })));
  });

  /* ---- лайтбокс ---- */
  const lb = document.querySelector('.lightbox');
  const lbImg = lb?.querySelector('img');
  document.querySelectorAll('[data-lightbox]').forEach((el) => {
    el.addEventListener('click', () => {
      if (!lb || !lbImg) return;
      lbImg.src = el.dataset.lightbox;
      lbImg.alt = el.querySelector('img')?.alt || '';
      lb.classList.add('is-open');
      body.style.overflow = 'hidden';
    });
  });
  const closeLb = () => { lb?.classList.remove('is-open'); lbImg?.removeAttribute('src'); body.style.overflow = ''; };
  lb?.querySelector('.lightbox__close')?.addEventListener('click', closeLb);
  lb?.addEventListener('click', (e) => { if (e.target === lb) closeLb(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeLb(); });

  /* ---- появление при скролле ---- */
  const items = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduce) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add('is-visible'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -4% 0px' });
    items.forEach((el) => io.observe(el));
  } else {
    items.forEach((el) => el.classList.add('is-visible'));
  }
})();
