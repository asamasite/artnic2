/* Run before the first paint; internal navigation never repeats the intro. */
(() => {
  let show = false;
  try {
    const key = 'artnik-visit-started';
    show = !sessionStorage.getItem(key);
    if (document.referrer && new URL(document.referrer).origin === location.origin) show = false;
    sessionStorage.setItem(key, '1');
  } catch { show = !document.referrer; }
  if (show) document.documentElement.classList.add('visit-intro');
})();
