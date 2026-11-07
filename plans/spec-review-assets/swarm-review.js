'use strict';
(() => {
  const data = globalThis.ATTENTION_APERTURE_DATA;
  const $ = selector => document.querySelector(selector);
  const all = selector => [...document.querySelectorAll(selector)];
  const make = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  const items = [...data.phases.map(item => ({ ...item, type: 'phase' })), ...data.capabilities.map(item => ({ ...item, type: 'capability' }))];
  const panel = $('#source-wording');
  const pick = $('#source-select');
  const stepLabel = make('label', 'inspect a step', 'step-picker');
  const stepPick = make('select');
  stepPick.id = 'step-picker';
  stepLabel.htmlFor = 'step-picker';
  for (const phase of data.phases) {
    const option = make('option', `${phase.number} / ${phase.title}`);
    option.value = phase.id; stepPick.append(option);
  }
  stepLabel.append(stepPick);
  $('.roadmap-layout').before(stepLabel);
  stepPick.addEventListener('change', () => $(`[data-phase="${stepPick.value}"]`).click());
  let currentSource = data.phases[0].sourceIds[0];
  const scroll = node => {
    node.scrollIntoView({ block: 'start', behavior: 'auto' });
    node.setAttribute('tabindex', '-1');
    node.focus({ preventScroll: true });
  };
  const jumpTo = item => {
    if (item.type === 'phase') $('[data-density="whole"]').click();
    else $('[data-capability-filter="all"]').click();
    $(`[data-${item.type}="${item.id}"]`).click();
    scroll($(`[data-${item.type}-detail]`));
  };
  const chooseSource = id => {
    currentSource = id;
    const passage = data.sources.find(source => source.id === id);
    pick.value = id;
    $('[data-source-title]').textContent = passage.title;
    $('[data-source-locator]').textContent = `${passage.path} · lines ${passage.start}–${passage.end}`;
    $('[data-source-excerpt]').textContent = passage.excerpt;
    const counterparts = $('[data-source-counterparts]');
    counterparts.replaceChildren();
    const related = items.filter(item => item.sourceIds.includes(id));
    for (const item of related) {
      const button = make('button', `${item.type === 'phase' ? 'step ' + item.number : 'choice'} / ${item.title || item.name}`);
      button.type = 'button';
      button.dataset.counterpart = item.id;
      button.addEventListener('click', () => jumpTo(item));
      counterparts.append(button);
    }
    if (!related.length) counterparts.append(make('p', 'context for the whole review; no single step or choice owns this passage.'));
    for (const item of items) {
      const button = $(`[data-${item.type}="${item.id}"]`);
      if (!button) continue;
      const supported = item.sourceIds.includes(id);
      button.classList.toggle('source-supported', supported);
      button.querySelector('.source-cue')?.remove();
      if (supported) button.append(make('span', '↗ source', 'source-cue'));
    }
  };
  const attachSources = type => {
    const button = $(`[data-${type}][aria-pressed="true"]`);
    const card = $(`[data-${type}-detail]`);
    if (!button || card.querySelector('.source-links')) return;
    const item = items.find(item => item.id === button.dataset[type] && item.type === type);
    const block = make('div', undefined, 'source-links');
    block.append(make('h4', 'supporting wording'));
    item.sourceIds.forEach(id => {
      const source = data.sources.find(source => source.id === id);
      const open = make('button', `${source.title} ↗`);
      open.type = 'button';
      open.dataset.openSource = id;
      open.addEventListener('click', () => { chooseSource(id); scroll($('#source-heading')); });
      block.append(open);
    });
    card.append(block);
  };
  for (const passage of data.sources) {
    const option = make('option', passage.title);
    option.value = passage.id;
    pick.append(option);
  }
  pick.addEventListener('change', () => chooseSource(pick.value));
  $('[data-coverage]').textContent = data.coverage;
  $('[data-source-revision]').textContent = `base revision ${data.sourceRevision.baseCommit}; working source sha256 ${data.sourceRevision.sha256}. the companion-link edit is included in this hash.`;
  document.addEventListener('click', event => {
    attachSources('phase');
    attachSources('capability');
    const target = event.target.closest('[data-phase], [data-capability], [data-capability-filter], [data-next-unmarked]');
    if (target) {
      const type = target.hasAttribute('data-phase') ? 'phase' : 'capability';
      const active = $(`[data-${type}][aria-pressed="true"]`);
      const item = items.find(item => item.type === type && item.id === active?.dataset[type]);
      if (item) {
        chooseSource(item.sourceIds.includes(currentSource) ? currentSource : item.sourceIds[0]);
        if (type === 'phase') {
          stepPick.value = item.id;
          if (matchMedia('(max-width: 980px)').matches && document.activeElement !== stepPick) scroll($('[data-phase-detail]'));
        }
      }
    } else if (event.target.closest('[data-review-mark]')) chooseSource(currentSource);
  });
  // The roadmap is the primary entry; the choice bench remains independently reachable.
  const roadmap = $('#roadmap');
  roadmap.parentNode.insertBefore(roadmap, $('#current-review'));
  $('[data-next-bite] a').href = '#roadmap';
  $('[data-next-bite] a').textContent = 'open the twelve-step route ↓';
  $('.skip-link').href = '#roadmap';
  const nav = make('nav', undefined, 'review-navigation');
  nav.setAttribute('aria-label', 'review sections');
  [['route', '#roadmap'], ['working choices', '#current-review'], ['source wording', '#source-wording'], ['four lanes', '#lanes-title']].forEach(([text, href]) => {
    const link = make('a', text); link.href = href; nav.append(link);
  });
  $('.masthead').after(nav);
  const sketch = make('div', undefined, 'weekend-thread');
  sketch.setAttribute('aria-label', 'proposed checkpoints: day one real replay; day two matched comparison');
  for (const [label, title] of [['day one', 'make a real episode replay.'], ['day two', 'compare what actually happened.']]) {
    const node = make('div'); node.append(make('span', label), make('strong', title)); sketch.append(node);
  }
  $('[data-next-bite]').append(sketch);
  attachSources('phase'); attachSources('capability'); chooseSource(currentSource);
})();
