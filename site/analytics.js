(() => {
  const id = document.querySelector('meta[name="ga-measurement-id"]')?.content.trim();
  if (!/^G-[A-Z0-9]+$/.test(id || '') || !['decisionbench.ai', 'www.decisionbench.ai'].includes(location.hostname)) return;

  const consentKey = 'decision-bench-analytics-consent';
  let started = false;
  let banner;
  const pageView = () => localStorage.getItem(consentKey) === 'yes' && window.gtag('event', 'page_view', {
    page_location: location.origin + location.pathname + location.hash.split('?')[0],
    page_path: location.pathname + location.hash.split('?')[0],
    page_title: document.title,
  });
  function start() {
    if (started) return;
    started = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    // Hash routes are the site's pages. Suppress automatic views to avoid duplicates.
    window.gtag('config', id, { send_page_view: false });
    pageView();
    window.addEventListener('hashchange', () => queueMicrotask(pageView));
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    document.head.appendChild(script);
  }
  function showChoice() {
    if (banner) return;
    banner = document.createElement('aside');
    banner.className = 'analytics-choice';
    banner.setAttribute('aria-label', 'Analytics choice');
    banner.innerHTML = '<p>May we use Google Analytics to understand visits to Decision Bench? <a href="privacy.html">Privacy details</a></p><div><button type="button" data-analytics-choice="no">No thanks</button><button type="button" data-analytics-choice="yes">Allow analytics</button></div>';
    document.body.appendChild(banner);
  }
  document.addEventListener('click', event => {
    const preference = event.target.closest('[data-analytics-preferences]');
    if (preference) { event.preventDefault(); showChoice(); return; }
    const choice = event.target.closest('[data-analytics-choice]')?.dataset.analyticsChoice;
    if (!choice) return;
    localStorage.setItem(consentKey, choice);
    banner?.remove();
    banner = null;
    if (choice === 'yes') { if (started) pageView(); else start(); }
  });
  if (localStorage.getItem(consentKey) === 'yes') start();
  else if (!localStorage.getItem(consentKey)) showChoice();
})();
