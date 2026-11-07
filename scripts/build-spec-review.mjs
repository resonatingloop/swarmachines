import { readFile, writeFile, copyFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const options = {};
for (let i = 0; i < args.length; i += 2) {
  if (!['--output', '--skill-root'].includes(args[i]) || !args[i + 1]) throw new Error('use --skill-root PATH --output EMPTY_PATH');
  options[args[i]] = path.resolve(args[i + 1]);
}
if (!options['--output'] || !options['--skill-root']) throw new Error('use --skill-root PATH --output EMPTY_PATH');
const input = path.join(root, 'plans/spec-review-data.json');
const data = JSON.parse(await readFile(input, 'utf8'));
const source = await readFile(path.join(root, 'specs/001-hackathon-plan.md'), 'utf8');
if (createHash('sha256').update(source).digest('hex') !== data.sourceRevision.sha256) {
  throw new Error('source changed: reconcile the review data and excerpts before rebuilding');
}
const lines = source.trimEnd().split('\n');
const ids = new Set();
for (const passage of data.sources) {
  if (!/^passage-\d{2}$/.test(passage.id) || ids.has(passage.id)) throw new Error('invalid or duplicate source id');
  ids.add(passage.id);
  const actual = source.split('\n').slice(passage.start - 1, passage.end).join('\n');
  if (actual !== passage.excerpt) throw new Error(`source excerpt differs: ${passage.id}`);
}
for (const item of [...data.phases, ...data.capabilities]) {
  if (!item.sourceIds?.length || item.sourceIds.some(id => !ids.has(id))) throw new Error(`missing source correspondence: ${item.id}`);
}
if (data.phases.length !== 12 || lines.filter(line => /^### \d+\./.test(line)).length !== 12) throw new Error('the twelve-step coverage changed');
const { buildAperture } = await import(pathToFileURL(path.join(options['--skill-root'], 'scripts/build-aperture.mjs')));
const result = await buildAperture({ dataPath: input, outputDirectory: options['--output'] });
const output = options['--output'];
let html = await readFile(path.join(output, 'index.html'), 'utf8');
html = html.replace('</head>', '  <link rel="stylesheet" href="swarm-review.css">\n  <script src="swarm-review.js" defer></script>\n</head>')
  .replace('sort the inherited pile', 'sort the working choices')
  .replace('purposes may survive without inherited code or topology.', 'these marks do not assign owners or accept the draft.')
  .replace('follow the programme sequence', 'from specimen to evidence')
  .replace('programme current', 'the proposed two-day route');
const sourcePanel = await readFile(path.join(root, 'plans/spec-review-assets/source-panel.html'), 'utf8');
html = html.replace('    <section class="deployments', sourcePanel + '\n    <section class="deployments');
await writeFile(path.join(output, 'index.html'), html);
let js = await readFile(path.join(output, 'aperture.js'), 'utf8');
js = js.replace('inherited specimen', 'proposed choice').replace('proposed destination', 'proposed treatment');
await writeFile(path.join(output, 'aperture.js'), js);
for (const asset of ['swarm-review.js', 'swarm-review.css']) {
  await copyFile(path.join(root, 'plans/spec-review-assets', asset), path.join(output, asset));
}
console.log(JSON.stringify({ ...result, sources: data.sources.length, sourceHashVerified: true }));
