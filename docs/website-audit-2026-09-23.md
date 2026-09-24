# Website quality audit — 23 September 2026

Audited https://decisionbench.ai/ and the production build in this repository. Improvements are local; production has not been deployed by this audit.

## Production baseline

Lighthouse 13.5.0, installed Chrome, cold page loads with Lighthouse's default simulated mobile/desktop throttling. These are laboratory measurements, not field Core Web Vitals.

| Category | Live mobile | Live desktop |
| --- | ---: | ---: |
| Performance | 58 | 71 |
| Accessibility | 90 | 87 |
| Best practices | 81 | 81 |
| SEO | 100 | 100 |
| Largest contentful paint | 15.5 s | 3.4 s |

Raw HTML/JSON reports and screenshots are saved locally under `tmp/site-audit/` (ignored by Git). Separate local before/after measurements use the same loopback server and gzip policy, to avoid attributing CDN or internet latency differences to code changes.

## Controlled local results

Mobile values below are the median of three serial cold Lighthouse runs per build. Desktop is one serial run per build. The same gzip-enabled loopback server served the saved original build and the improved build, with the same benchmark data. The final runs did not overlap browser regression tests.

| Metric | Mobile before | Mobile after | Desktop before | Desktop after |
| --- | ---: | ---: | ---: | ---: |
| Performance | 65 | **74** | 86 | **95** |
| Accessibility | 90 | **100** | 87 | **100** |
| Best practices | 100 | **100** | 100 | **100** |
| SEO | 100 | **100** | 100 | **100** |
| First contentful paint | 3.0 s | **1.8 s** | 0.6 s | **0.4 s** |
| Largest contentful paint | 13.4 s | **8.3 s** | 2.4 s | **1.5 s** |
| Total blocking time | 194 ms | **118 ms** | 0 ms | **0 ms** |
| Cumulative layout shift | 0.015 | **0.000** | 0.000 | 0.022 |

Mobile performance runs were 65/67/65 before and 74/74/74 after. LCP improved approximately 38%, but **mobile LCP remains poor**; this is not a claim that the site now passes field Core Web Vitals. Desktop's small remaining layout shift is below 0.1 and reflects a tradeoff to monitor with nonblocking fonts.

Initial data decreased from **16,307,615 to 8,490,227 bytes** (48% smaller). With gzip it decreased from **1,848,749 to 930,324 bytes** (50% smaller). The original JavaScript requests included the 282 KB Tailwind browser compiler; that request has been eliminated entirely.

## Implemented

- Replaced the production Tailwind browser compiler with pinned Tailwind/Vite build dependencies. Styles are scanned from explicitly declared source files and emitted as minified, hashed CSS. No runtime CDN compiler is required. Tailwind itself [documents its browser CDN as development-only](https://tailwindcss.com/docs/installation/play-cdn).
- Removed the artificial splash delay and stylesheet mutation observer. Data requests run concurrently, revalidate cache entries, time out, and show a retry action on failure. Page chunks have a recoverable error boundary.
- Added an 8.49 MB viewer index instead of requiring the full 16.31 MB download at startup. Record bodies, provenance, raw answers, and score probabilities are fetched per row, under content-addressed filenames. Complete `data.json` and `corpus.json` downloads remain unchanged. Browser state keeps object identities, and concurrent row requests share a promise. Corpus, row, and result identities are checked before applying a detail response.
- Split secondary pages into lazy chunks. The initial application JavaScript is approximately 475 KB before compression, down from approximately 643 KB. Actual transfer totals are recorded in the Lighthouse files.
- Made external font CSS nonblocking. System fallback fonts can paint first; layout shift is measured separately rather than assuming this has no cost.
- Replaced filter/sort tabs that referenced nonexistent tab panels with named radio groups. Arrow navigation and selected state are covered by browser checks.
- Exposed focusable chart points to assistive technology and provided descriptive names. Made horizontally scrolling result graphics and code blocks keyboard-focusable.
- Corrected the use-case button's accessible name, model-answer disclosure buttons, mobile list control attributes, and review progress label.
- Adjusted muted text, error badges, and heatmap fills after measuring failing foreground/background pairs in both themes. Underlined an inline link that previously relied on color alone.
- Added useful HTML content and download links for JavaScript-disabled visitors, a more descriptive initial title, privacy-page metadata/canonical URL, and the privacy page in the sitemap.
- Added data-integrity, build, and browser regression checks. CI and Pages workflows now run all viewer unit tests alongside analytics tests.

## Verification

- **103 Python tests passed**, including viewer reconstruction and content-addressing tests.
- **8 JavaScript unit tests passed**, including existing analytics/consent tests and integrity checks covering all 1,071 generated rows and their published model answers.
- **40 browser route/theme/viewport combinations passed**, with no axe violations, JavaScript exceptions, or page-level horizontal overflow.
- Keyboard filtering and skip navigation, raw-answer disclosure, exact input preservation, search, theme persistence, unavailable-data recovery, row retry, legacy full-data fallback, and no-JavaScript fallback passed.
- Six additional reflow checks at **320px and 768px** passed for home, tasks, and compare.
- Corpus/result validation returned **no problems**; the repository secret scan returned **zero findings**; the final npm audit returned **zero known vulnerabilities**.
- Production and preview screenshots were visually inspected. Production HTTP 200, content type, cache policy, and security headers were checked with curl. Generic Python HEAD requests were separately blocked (see caveat below).


The generated-data regression checks compare every reconstructed row and every model answer against the complete original download, not just the fixture used by the Python unit test. Published scores and benchmark decisions are unchanged.

Browser checks cover ten route types at 390px and 1440px, in light and dark themes, including a task, row, model, compare, data, methodology, and review. Axe checks WCAG 2 A/AA and WCAG 2.1 A/AA rules. The suite also exercises skip navigation, arrow-key filters, lazy row details, answer disclosure, exact model input, search, theme persistence, unavailable data, row retry, compatibility with older full-data builds, and JavaScript-disabled HTML.

Automated checks do not establish full WCAG conformance. Human screen-reader testing, broad device/browser coverage, field INP, and production load capacity are not measured here. No stress traffic or invasive penetration testing was sent to production.

## Remaining improvements

1. **Independent SEO content.** A later change replaced URL fragments with clean paths and generated direct-load HTML shells, canonical URLs, titles, and sitemap entries while preserving old shared hash links. The page bodies are still rendered by JavaScript; fully crawlable server-rendered task/model/row content remains a separate improvement. [Google recommends real URLs rather than fragments for content changes](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics).
2. **Reduce initial score data further.** The viewer index is smaller but still substantial. Next, precompute homepage statistics and load per-task scores only when needed; preserve arbitrary filter and model-comparison accuracy through equivalence tests. This is a separate data contract change.
3. **CDN/security headers.** Successful production responses expose `Access-Control-Allow-Origin: *` and did not include CSP, HSTS, `X-Content-Type-Options`, or `Referrer-Policy`. The app is a public static site; no authenticated data exposure was demonstrated. Apply explicit header rules at Cloudflare/hosting, remove unnecessary wildcard CORS or use an explicit allowlist, add `nosniff` and a suitable referrer policy, validate HTTPS coverage before HSTS, and roll out CSP in report-only mode before enforcement. Inline theme/boot scripts and analytics/font origins must be accounted for. GitHub Pages does not read a generic `_headers` file, so none was added with a false promise of protection.
4. **Third-party production warnings.** Lighthouse's deprecation warnings originate in Cloudflare's `cdn-cgi/challenge-platform` script. They do not occur in the local build. Local best-practices improvements must not be presented as proof that production warnings are fixed.
5. **Crawling access.** Generic Python HEAD requests received 403 while Chrome and curl accessed the homepage successfully. This is client-dependent behavior, not proof that Googlebot is blocked. Verify crawler access using Search Console and Cloudflare's verified-bot settings.
6. **Fonts and logos.** Consider licensed self-hosted font subsets and smaller modern-format logo variants. Lighthouse flagged approximately 67 KiB of avoidable logo transfer in the live mobile baseline. Recheck branding, sharpness, font layout shifts, and caching after that change.
7. **Real-user performance.** Rerun Lighthouse after deployment and inspect field LCP/INP/CLS once enough visits exist. The live scores above remain the production baseline until deployed and remeasured.

🔒 SECURITY REVIEW
Issue: Public hosting returns wildcard CORS and lacks observed browser security headers.
Severity: MEDIUM
Location: production HTTP response configuration (outside the repository diff)
Risk: Missing browser defense-in-depth; no authentication bypass or private-data leak was found in this public static viewer.
Fix: Configure the CDN response rules described above and verify their actual HTTP responses before enforcement.

## Reproduce

```sh
python3 -m decision_bench report
npm ci --prefix web
npm run build --prefix web
npm test --prefix web
python3 -m unittest discover -s tests -q
python3 -m decision_bench validate
python3 scripts/check_secrets.py
npm audit --prefix web
```

For browser regression checks, run `npm run preview --prefix web` in a separate terminal, install Chromium once with `web/node_modules/.bin/playwright install chromium`, then run `npm run test:site --prefix web`. Alternatively set `CHROME_PATH` to an installed Chrome executable. `SITE_URL` selects a different preview origin. Reports go to `tmp/site-audit/`.

For Lighthouse, use the pinned CLI: `npm run audit --prefix web -- https://decisionbench.ai/ --output=html --output=json --output-path=../tmp/site-audit/live-mobile`. Add `--preset=desktop` for desktop. Run performance audits serially with other browser tests stopped; repeat runs and compare medians. Use a server with production-equivalent compression when comparing local network timings.
