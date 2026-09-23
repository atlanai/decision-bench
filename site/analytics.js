(() => {
  const id = document.querySelector('meta[name="ga-measurement-id"]')?.content.trim();
  if (!/^G-[A-Z0-9]+$/.test(id || '') || !['decisionbench.ai', 'www.decisionbench.ai'].includes(location.hostname)) return;

  const consentKey = 'decision-bench-analytics-consent';
  let started = false;
  let banner;
  let page, lastPath;
  const consent = () => { try { return localStorage.getItem(consentKey); } catch { return 'no'; } };
  const send = (name, params) => {
    if (!started || consent() !== 'yes' || !page) return;
    window.gtag('event', name, {...page, ...params, page_referrer: ''});
  };
  const pageView = () => { if (!page || consent() !== 'yes' || lastPath === page.page_path) return; send('page_view', {}); lastPath = page.page_path; };
  window.dbAnalytics = {
    page(value) { page = value; if (started && consent() === 'yes') { window.gtag('set', {page_location: page.page_location, page_title: page.page_title, page_referrer: ''}); pageView(); } },
    event: send,
  };
  function start() {
    if (started) return;
    started = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    // Hash routes are the site's pages. Suppress automatic views to avoid duplicates.
    window.gtag('config', id, { send_page_view: false, allow_google_signals: false, allow_ad_personalization_signals: false, page_location: location.origin + '/', page_referrer: '', page_title: 'Decision Bench', ...(page || {}) });
    pageView();
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
    try { localStorage.setItem(consentKey, choice); } catch { return; }
    window[`ga-disable-${id}`] = choice !== 'yes';
    if (choice !== 'yes') lastPath = undefined;
    banner?.remove();
    banner = null;
    if (choice === 'yes') { if (started) pageView(); else start(); }
  });
  if (location.pathname.endsWith('/privacy.html')) window.dbAnalytics.page({page_type: 'privacy', page_path: '/privacy.html', page_location: location.origin + '/privacy.html', page_title: 'Privacy · Decision Bench'});
  if (consent() === 'yes') start();
  else if (!consent()) showChoice();
})();
