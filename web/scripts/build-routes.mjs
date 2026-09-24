/* GitHub Pages serves files, not an SPA rewrite. Give every published route an
   index.html so clean deep links return 200 and refresh without a hash. */
import {existsSync, mkdirSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';

const site = fileURLToPath(new URL('../../site/', import.meta.url));
const root = readFileSync(join(site, 'index.html'), 'utf8');
if (!root.includes('<base href="/">')) throw Error('Built entry must resolve assets from the site root');

const read = name => existsSync(join(site, name)) ? JSON.parse(readFileSync(join(site, name), 'utf8')) : null;
const data = read('data.json'), datasets = read('datasets.json');
const roots = ['tasks', 'task', 'row', 'models', 'model', 'compare', 'data', 'methodology', 'review'];
for (const name of roots) rmSync(join(site, name), {recursive: true, force: true});

const routes = new Map();
const add = (path, title) => routes.set(path, title);
for (const [path, title] of [['tasks', 'Tasks'], ['models', 'Models'], ['compare', 'Compare models'], ['data', 'Datasets'], ['methodology', 'Methodology'], ['review', 'Review']]) add(path, title);
const id = value => {
  if (!/^[A-Za-z0-9._-]+$/.test(value)) throw Error(`Unsafe route identifier: ${value}`);
  return value;
};
for (const task of new Set(data?.cases?.map(c => c.task) || [])) add(`task/${id(task)}`, `Task ${task}`);
for (const row of data?.cases || []) {
  add(`row/${id(row.id)}`, `Row ${row.id}`);
  add(`review/${id(row.id)}`, `Review ${row.id}`);
}
const configuredModels = new Map((data?.models || []).map(model => [model.id, model]));
for (const run of (data?.runs || []).filter(run => String(run.status || '').startsWith('completed'))) {
  const modelId = run.model_id || run.model?.id;
  const model = configuredModels.get(modelId) || run.model || {};
  add(`model/${id(modelId)}`, model.label || modelId);
}
for (const dataset of datasets?.datasets || []) add(`data/${id(dataset.id)}`, dataset.name || dataset.id);
for (const section of ['what', 'rows', 'sees', 'metrics', 'verdict', 'limits', 'submit']) add(`methodology/${section}`, 'Methodology');

const esc = text => text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
for (const [path, title] of routes) {
  const url = `https://decisionbench.ai/${path}/`;
  const html = root
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(title)} · Decision Bench</title>`)
    .replace('<link rel="canonical" href="https://decisionbench.ai/">', `<link rel="canonical" href="${url}">`)
    .replace('<meta property="og:url" content="https://decisionbench.ai/">', `<meta property="og:url" content="${url}">`);
  const dir = join(site, path);
  mkdirSync(dir, {recursive: true});
  writeFileSync(join(dir, 'index.html'), html);
}
writeFileSync(join(site, '404.html'), root);
const sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  '  <url><loc>https://decisionbench.ai/</loc></url>',
  ...[...routes.keys()].filter(path => path !== 'review' && !path.startsWith('review/')).map(path => `  <url><loc>https://decisionbench.ai/${path}/</loc></url>`),
  '</urlset>', ''].join('\n');
writeFileSync(join(site, 'sitemap.xml'), sitemap);
console.log(`Generated ${routes.size} clean route entries and a fallback page`);
