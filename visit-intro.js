/* Show on site entry or reload, but never on internal navigation or Back. */
(() => {
  const transitionKey = 'denta-internal-transition';
  let clickedInside = false;
  try {
    const saved = JSON.parse(sessionStorage.getItem(transitionKey) || 'null');
    sessionStorage.removeItem(transitionKey);
    const current = location.href.split('#')[0];
    clickedInside = saved?.url === current && Date.now() - saved.time < 15000;
  } catch {}
  // Referrer may be absent for local files or suppressed by browser settings.
  // Record explicit internal clicks, including both header and footer logos.
  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
    try {
      const target = new URL(link.href, location.href);
      if (target.origin !== location.origin || !['http:', 'https:', 'file:'].includes(target.protocol)) return;
      const current = location.href.split('#')[0];
      const destination = target.href.split('#')[0];
      if (destination === current && target.hash) return;
      sessionStorage.setItem(transitionKey, JSON.stringify({url: destination, time: Date.now()}));
    } catch {}
  });
  let internal = false;
  try {
    internal = !!document.referrer && new URL(document.referrer).origin === location.origin;
  } catch {}
  const navigation = performance.getEntriesByType('navigation')[0];
  const show = !clickedInside && navigation?.type !== 'back_forward' && (navigation?.type === 'reload' || !internal);
  if (!show) return;
  document.documentElement.classList.add('visit-intro');
  addEventListener('DOMContentLoaded', () => {
    const preloader = document.querySelector('.preloader');
    if (!preloader) return;
    setTimeout(() => { preloader.hidden = true; preloader.style.display = 'none'; }, 1400);
  }, {once: true});
})();
