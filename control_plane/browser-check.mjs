// Run only against observer-generated local HTML in an isolated browser profile.
import fs from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const target = process.argv[2];
if (!target) throw Error('usage: node control_plane/browser-check.mjs snapshot/index.html');
const profile = await fs.mkdtemp(path.join(tmpdir(), 'control-observer-browser-'));
const chrome = spawn(process.env.CHROME_BIN || '/usr/bin/google-chrome', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--no-first-run',
  '--disable-background-networking', '--disable-default-apps',
  '--remote-debugging-port=0', '--user-data-dir=' + profile, 'about:blank',
], { stdio: 'ignore' });
let ws;
try {
  let port;
  for (let i = 0; i < 60; i++) {
    try { port = (await fs.readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; break; }
    catch { await new Promise(r => setTimeout(r, 100)); }
  }
  assert(port, 'browser started');
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(tabs.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let sequence = 0;
  const pending = new Map(), requests = [], errors = [];
  ws.onmessage = e => {
    const message = JSON.parse(e.data);
    if (message.id) {
      const p = pending.get(message.id); pending.delete(message.id);
      clearTimeout(p.timer);
      message.error ? p.reject(Error(JSON.stringify(message.error))) : p.resolve(message.result);
    } else if (message.method === 'Network.requestWillBeSent') requests.push(message.params.request.url);
    else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(Error('browser command timed out')); }, 10000);
    pending.set(id, { resolve, reject, timer }); ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true });
    assert(!result.exceptionDetails, 'evaluation completed');
    return result.result.value;
  };
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Page.navigate', { url: pathToFileURL(path.resolve(target)).href });
  for (let i = 0; i < 50; i++) {
    if (await evaluate('document.readyState === "complete" && !!document.querySelector(".lanes")')) break;
    await new Promise(r => setTimeout(r, 100));
  }
  assert.equal(await evaluate('document.querySelectorAll("script").length'), 0);
  assert.equal(await evaluate('document.querySelectorAll(".lane").length'), 4);
  assert(await evaluate('document.body.textContent.includes("not observed")'));
  for (const width of [1440, 720, 320]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
    assert(await evaluate('document.documentElement.scrollWidth <= innerWidth'), `no page overflow at ${width}`);
    if (width === 1440 || width === 320) {
      const screenshot = await send('Page.captureScreenshot', { format: 'png' });
      await fs.writeFile(path.join(path.dirname(path.resolve(target)), width === 1440 ? 'desktop.png' : 'mobile.png'), Buffer.from(screenshot.data, 'base64'));
    }
  }
  await send('Page.bringToFront');
  await evaluate('document.querySelector("summary").focus()');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 });
  assert.equal(await evaluate('document.querySelector("details").open'), false, 'keyboard toggles diagnostics');
  assert.equal(errors.length, 0, 'no browser errors');
  assert(requests.every(url => url.startsWith('file:')), 'no external requests');
  console.log('browser checks passed: script-free, four lanes, provenance warning, 1440/720/320 reflow, keyboard, no external requests');
} finally {
  if (ws) ws.close();
  chrome.kill();
  await new Promise(resolve => chrome.exitCode !== null ? resolve() : chrome.once('exit', resolve));
  await fs.rm(profile, { recursive: true, force: true });
}
