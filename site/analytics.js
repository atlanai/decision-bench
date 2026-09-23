(() => {
  const id = document.querySelector('meta[name="ga-measurement-id"]')?.content.trim();
  if (!/^G-[A-Z0-9]+$/.test(id || '') || !['decisionbench.ai', 'www.decisionbench.ai'].includes(location.hostname)) return;

  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  // Hash routes are the site's pages. Send each page view once, without URL query data.
  window.gtag('config', id, { send_page_view: false });
  const pageView = () => window.gtag('event', 'page_view', {
    page_location: location.origin + location.pathname + location.hash.split('?')[0],
    page_path: location.pathname + location.hash.split('?')[0],
    page_title: document.title,
  });
  pageView();
  window.addEventListener('hashchange', pageView);

  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.appendChild(script);
})();
