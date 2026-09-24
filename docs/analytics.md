# Site analytics

The existing GA4 web stream is configured by `ga-measurement-id` in `web/index.html`. The loader runs only on decisionbench.ai and www.decisionbench.ai, after explicit opt-in. No new package or server is required.

Page views are emitted after React commits a loaded route, once per canonical path transition, including browser back/forward. Filter-only changes do not create page views. Accepting consent records the current page; withdrawing it blocks custom events and disables the Google tag. Previously declined interactions are not replayed. Blocked browser storage fails closed.

| Event | Meaning / additional metadata |
| --- | --- |
| `page_view` | Page type, canonical path/title, benchmark version; validated public model, task, row, dataset, category or methodology section where applicable |
| `navigation_click` | Destination page/path, header/footer/content area and validated destination filters |
| `outbound_click` | Destination domain and area; no external path or query |
| `file_download` | Public file name and area |
| `filter_change` | Valid category/modality, selected model count, search active boolean |
| `comparison_change` | Valid model A/B IDs |
| `model_selection` | Number of selected models |
| `ui_click` | Explicit control ID: sort, columns, details, menus, theme, random task, record expansion, citations, methodology, review import/export |
| `chart_click` | Every-row chart and public row/task IDs |
| `result_toggle` | Result expanded/collapsed (mouse or keyboard) |
| `review_action` | Previous/next/ok/flag (mouse or keyboard); no note or content |
| `review_filter` | All/todo/flagged |

All custom events carry the current page metadata. No DOM text, search terms, notes, uploaded content, raw URL queries, or document referrers are copied to payloads. Unknown URL IDs are discarded. Copy/import/export events measure the action, not its contents or successful completion. Interactions with tooltips and hover motion are deliberately omitted.

## GA4 property setup and verification

Disable **Enhanced measurement** for this stream in GA4 so automatic history views, outbound clicks, downloads, form and search events do not duplicate the explicit instrumentation or collect unsanitized URLs. This is a property setting; the repository cannot change it. Automatic GA session/engagement events may still exist. The tag configuration and explicit events use sanitized page metadata and an empty referrer.

Register event-scoped custom dimensions for the parameters needed in reports: `page_type`, `benchmark_version`, `task_id`, `model_id`, `dataset_id`, `category`, `control`, `area`, `destination_page`, `filter_category`, `filter_modality`, `model_a`, `model_b`, `search_active`, `action`, `filter`, `chart`, and `expanded`. Use a custom metric for `selected_model_count`. Avoid registering row IDs as dimensions unless required, because of their cardinality.

Verify in GA4 Realtime (or DebugView with debug mode enabled): accept consent, navigate pages, change filters, compare models, download a file, and withdraw consent. Check that each navigation emits one page view, filter changes emit no page view, and new events stop after withdrawal. This requires access to the GA4 property; local tests do not prove Google received events.

Run `node --test web/tests/analytics.test.mjs` and `npm --prefix web run build`. Analytics tests also run in CI and the Pages workflow.

Google references: [manual page views](https://developers.google.com/analytics/devguides/collection/ga4/views), [Enhanced measurement](https://support.google.com/analytics/answer/9216061), and [disabling collection](https://developers.google.com/tag-platform/security/guides/privacy).
