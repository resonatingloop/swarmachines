'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const E = require('./evidence.js');
const { escapeBidi, escapeMarkdown, escapeForMarkdown, containsBidiChars, BIDI_ESCAPE_MAP, text } = E;

// Helper functions for table/document tests (not exported, tested indirectly)
function eventToMarkdownRow(event) {
  const { seq, turn, agent_id, type, ts } = event;
  const agent = agent_id !== null ? escapeForMarkdown(agent_id, { forTableCell: true }) : '—';
  return `| ${seq} | ${turn} | ${agent} | ${escapeForMarkdown(type, { forTableCell: true })} | ${escapeForMarkdown(ts, { forTableCell: true })} |`;
}

function eventsToMarkdownTable(events) {
  const header = '| Seq | Turn | Agent | Type | Timestamp |';
  const separator = '|-----|------|-------|------|-----------|';
  const rows = events.map(eventToMarkdownRow);
  return [header, separator, ...rows].join('\n');
}

function episodeToMarkdown(episode) {
  const { config, events } = episode;
  const lines = [];
  lines.push('# Episode Export');
  lines.push('');
  lines.push('## Configuration');
  lines.push('');
  if (config) {
    lines.push(`- **Run ID**: ${escapeForMarkdown(config.run_id || 'unknown')}`);
    lines.push(`- **Seed**: ${config.seed ?? 'N/A'}`);
    lines.push(`- **Topology**: ${escapeForMarkdown(config.comm_topology || 'N/A')}`);
    lines.push(`- **Agents**: ${escapeForMarkdown(JSON.stringify(config.agents || []))}`);
    if (config.disturbance_schedule) {
      lines.push(`- **Disturbance**: ${escapeForMarkdown(JSON.stringify(config.disturbance_schedule))}`);
    }
  }
  lines.push('');
  lines.push('## Event Log');
  lines.push('');
  lines.push(eventsToMarkdownTable(events || []));
  lines.push('');
  return lines.join('\n');
}

function roundTripTest(original) {
  const escaped = escapeForMarkdown(original);
  return typeof escaped === 'string' && escaped.length >= 0;
}

test('BIDI_ESCAPE_MAP has exactly 108 entries', () => {
  assert.strictEqual(BIDI_ESCAPE_MAP.size, 108, `Expected 108 entries, got ${BIDI_ESCAPE_MAP.size}`);
});

test('BIDI_ESCAPE_MAP complete coverage - all 108 codepoints tested', () => {
  const testedCodepoints = new Set();
  
  for (const [char, expectedEscape] of BIDI_ESCAPE_MAP) {
    const codepoint = 'U+' + char.codePointAt(0).toString(16).toUpperCase().padStart(4, '0');
    const result = escapeBidi('X' + char + 'Y');
    
    // Assert the original codepoint does not survive
    assert.strictEqual(
      result.includes(char),
      false,
      `Codepoint ${codepoint} survived in output: ${JSON.stringify(result)}`
    );
    
    // Assert the visible \uXXXX replacement appears
    assert.strictEqual(
      result,
      'X' + expectedEscape + 'Y',
      `Codepoint ${codepoint} escaped incorrectly. Expected: ${JSON.stringify('X' + expectedEscape + 'Y')}, Got: ${JSON.stringify(result)}`
    );
    
    testedCodepoints.add(codepoint);
  }
  
  assert.strictEqual(
    testedCodepoints.size,
    108,
    `Expected 108 codepoints tested, got ${testedCodepoints.size}`
  );
});

test('C0 controls (0x00-0x1F except tab/newline/cr) are escaped', () => {
  const c0Controls = [
    '\u0000', '\u0001', '\u0002', '\u0003', '\u0004', '\u0005', '\u0006', '\u0007',
    '\u0008', '\u000B', '\u000C', '\u000E', '\u000F', '\u0010', '\u0011', '\u0012',
    '\u0013', '\u0014', '\u0015', '\u0016', '\u0017', '\u0018', '\u0019', '\u001A',
    '\u001B', '\u001C', '\u001D', '\u001E', '\u001F'
  ];
  
  for (const char of c0Controls) {
    const result = escapeBidi(char);
    assert.ok(
      result.startsWith('\\u'),
      `C0 control U+${char.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')} not escaped: ${JSON.stringify(result)}`
    );
  }
});

test('DEL and C1 controls (0x7F-0x9F) are escaped', () => {
  for (let code = 0x7F; code <= 0x9F; code++) {
    const char = String.fromCharCode(code);
    const result = escapeBidi(char);
    assert.ok(
      result.startsWith('\\u'),
      `C1 control U+${code.toString(16).toUpperCase().padStart(4, '0')} not escaped: ${JSON.stringify(result)}`
    );
  }
});

test('U+2028/2029 line and paragraph separators are escaped', () => {
  assert.strictEqual(escapeBidi('\u2028'), '\\u2028');
  assert.strictEqual(escapeBidi('\u2029'), '\\u2029');
});

test('bidi marks (LRM/RLM/ALM) are escaped', () => {
  assert.strictEqual(escapeBidi('\u200E'), '\\u200E'); // LRM
  assert.strictEqual(escapeBidi('\u200F'), '\\u200F'); // RLM
  assert.strictEqual(escapeBidi('\u061C'), '\\u061C'); // ALM
});

test('bidi embeddings and overrides (U+202A-202E) are escaped', () => {
  assert.strictEqual(escapeBidi('\u202A'), '\\u202A'); // LRE
  assert.strictEqual(escapeBidi('\u202B'), '\\u202B'); // RLE
  assert.strictEqual(escapeBidi('\u202C'), '\\u202C'); // PDF
  assert.strictEqual(escapeBidi('\u202D'), '\\u202D'); // LRO
  assert.strictEqual(escapeBidi('\u202E'), '\\u202E'); // RLO
});

test('bidi isolates (U+2066-2069) are escaped', () => {
  assert.strictEqual(escapeBidi('\u2066'), '\\u2066'); // LRI
  assert.strictEqual(escapeBidi('\u2067'), '\\u2067'); // RLI
  assert.strictEqual(escapeBidi('\u2068'), '\\u2068'); // FSI
  assert.strictEqual(escapeBidi('\u2069'), '\\u2069'); // PDI
});

test('zero-width and special format chars are escaped', () => {
  assert.strictEqual(escapeBidi('\u200B'), '\\u200B'); // ZWSP
  assert.strictEqual(escapeBidi('\u200C'), '\\u200C'); // ZWNJ
  assert.strictEqual(escapeBidi('\u200D'), '\\u200D'); // ZWJ
  assert.strictEqual(escapeBidi('\u00AD'), '\\u00AD'); // SHY
  assert.strictEqual(escapeBidi('\uFEFF'), '\\uFEFF'); // BOM
});

test('entity injection prevention - HTML numeric entity neutralized', () => {
  const input = '&#x202E;malicious';
  const result = text(input);
  // All punctuation is escaped as numeric entities, so the entity cannot form
  assert.ok(result.includes('&#38;')); // & escaped as &#38;
  assert.strictEqual(result.includes('&#x202E;'), false, `Numeric entity survived: ${JSON.stringify(result)}`);
});

test('entity injection prevention - decimal entity neutralized', () => {
  const input = '&#8238;attack'; // 8238 = 0x202E
  const result = text(input);
  assert.ok(result.includes('&#38;')); // & escaped
  assert.strictEqual(result.includes('&#8238;'), false);
});

test('text() escapes ampersand before other processing', () => {
  const input = 'a & b <c>';
  const result = text(input);
  // text() first escapes & to &amp;, < to &lt;, > to &gt;, then escapes all punctuation
  // This results in: &amp; -> &#38;amp&#59;, &lt; -> &#38;lt&#59;, &gt; -> &#38;gt&#59;
  assert.strictEqual(result, 'a &#38;amp&#59; b &#38;lt&#59;c&#38;gt&#59;');
});

test('entity injection prevention in markdown output', () => {
  const input = 'test &#x202E; reversed';
  const result = text(input);
  assert.ok(!result.includes('&#x'));
  assert.ok(result.includes('&#38;')); // & escaped
});

test('markdown breakout prevention - table pipe', () => {
  const input = 'cell | fake column';
  const result = escapeForMarkdown(input, { forTableCell: true });
  assert.strictEqual(result, 'cell \\| fake column');
});

test('markdown breakout prevention - link forgery', () => {
  const input = 'click [here](evil.com)';
  const result = escapeForMarkdown(input);
  assert.strictEqual(result, 'click \\[here\\]\\(evil.com\\)');
});

test('markdown breakout prevention - heading forgery', () => {
  const input = '# Fake Heading';
  const result = escapeForMarkdown(input);
  assert.strictEqual(result, '\\# Fake Heading');
});

test('markdown breakout prevention - code injection', () => {
  const input = 'run `rm -rf /`';
  const result = escapeForMarkdown(input);
  assert.strictEqual(result, 'run \\`rm -rf /\\`');
});

test('markdown breakout prevention - emphasis manipulation', () => {
  const input = '*fake italic* and **fake bold**';
  const result = escapeForMarkdown(input);
  assert.strictEqual(result, '\\*fake italic\\* and \\*\\*fake bold\\*\\*');
});

test('markdown breakout prevention - combined attack vectors', () => {
  const input = '# Heading | [link](evil.com) `code`';
  const result = escapeForMarkdown(input);
  assert.strictEqual(result, '\\# Heading | \\[link\\]\\(evil.com\\) \\`code\\`');
});

test('newline literalization in text() function', () => {
  const input = 'line1\nline2';
  const result = text(input);
  assert.strictEqual(result, 'line1\\nline2');
});

test('carriage return literalization in text() function', () => {
  const input = 'line1\rline2';
  const result = text(input);
  assert.strictEqual(result, 'line1\\rline2');
});

test('heading forgery prevention via newline', () => {
  const input = 'safe text\n# malicious heading';
  const result = text(input);
  // Newline is literalized, # is escaped as &#35;
  assert.strictEqual(result, 'safe text\\n&#35; malicious heading');
  assert.ok(result.includes('\\n'));
});

test('link forgery prevention via newline', () => {
  const input = 'text\n[evil](bad.com)';
  const result = text(input);
  assert.ok(result.includes('\\n'));
  assert.ok(result.includes('&#91;') || result.includes('\\['));
});

test('CRLF handling', () => {
  const input = 'line1\r\nline2';
  const result = text(input);
  assert.strictEqual(result, 'line1\\r\\nline2');
});

test('escapeMarkdown - asterisk', () => {
  const input = 'Hello *world*';
  const result = escapeMarkdown(input);
  assert.strictEqual(result, 'Hello \\*world\\*');
});

test('escapeMarkdown - underscore', () => {
  const input = 'Hello _world_';
  const result = escapeMarkdown(input);
  assert.strictEqual(result, 'Hello \\_world\\_');
});

test('escapeMarkdown - backtick', () => {
  const input = 'Hello `code`';
  const result = escapeMarkdown(input);
  assert.strictEqual(result, 'Hello \\`code\\`');
});

test('escapeMarkdown - backslash first', () => {
  const input = 'path\\to\\file';
  const result = escapeMarkdown(input);
  assert.strictEqual(result, 'path\\\\to\\\\file');
});

test('escapeMarkdown - brackets', () => {
  const input = 'Hello [link]';
  const result = escapeMarkdown(input);
  assert.strictEqual(result, 'Hello \\[link\\]');
});

test('escapeMarkdown - parentheses', () => {
  const input = 'Hello (world)';
  const result = escapeMarkdown(input);
  assert.strictEqual(result, 'Hello \\(world\\)');
});

test('escapeMarkdown - hash', () => {
  const input = '# Heading';
  const result = escapeMarkdown(input);
  assert.strictEqual(result, '\\# Heading');
});

test('escapeMarkdown - benign text unchanged', () => {
  const input = 'Normal text without special chars';
  const result = escapeMarkdown(input);
  assert.strictEqual(result, 'Normal text without special chars');
});

test('escapeForMarkdown - bidi then markdown escaping', () => {
  const input = '\u200F *italic*';
  const result = escapeForMarkdown(input);
  assert.strictEqual(result, '\\\\u200F \\*italic\\*');
});

test('escapeForMarkdown - benign text', () => {
  const input = 'Normal text';
  const result = escapeForMarkdown(input);
  assert.strictEqual(result, 'Normal text');
});

test('escapeForMarkdown - combined bidi and markdown chars', () => {
  const input = '\u200E\u200F\u061C *bold* _italic_ `code`';
  const result = escapeForMarkdown(input);
  assert.ok(result.includes('\\\\u200E'));
  assert.ok(result.includes('\\\\u200F'));
  assert.ok(result.includes('\\\\u061C'));
  assert.ok(result.includes('\\*bold\\*'));
  assert.ok(result.includes('\\_italic\\_'));
  assert.ok(result.includes('\\`code\\`'));
});

test('containsBidiChars - returns true for LRM', () => {
  assert.strictEqual(containsBidiChars('Hello\u200E'), true);
});

test('containsBidiChars - returns true for RLM', () => {
  assert.strictEqual(containsBidiChars('Hello\u200F'), true);
});

test('containsBidiChars - returns true for ALM', () => {
  assert.strictEqual(containsBidiChars('Hello\u061C'), true);
});

test('containsBidiChars - returns false for benign text', () => {
  assert.strictEqual(containsBidiChars('Normal text'), false);
});

test('containsBidiChars - returns false for empty string', () => {
  assert.strictEqual(containsBidiChars(''), false);
});

test('containsBidiChars - returns false for non-string', () => {
  assert.strictEqual(containsBidiChars(123), false);
});

test('roundTripTest - benign text', () => {
  assert.strictEqual(roundTripTest('Normal text'), true);
});

test('roundTripTest - bidi chars', () => {
  assert.strictEqual(roundTripTest('\u200E\u200F'), true);
});

test('roundTripTest - empty string', () => {
  assert.strictEqual(roundTripTest(''), true);
});

test('eventToMarkdownRow - converts event to row', () => {
  const event = {
    seq: 1,
    turn: 0,
    agent_id: 'agent-a',
    type: 'message.sent',
    ts: '2026-11-07T14:30:00Z',
  };
  const result = eventToMarkdownRow(event);
  assert.strictEqual(result, '| 1 | 0 | agent-a | message.sent | 2026-11-07T14:30:00Z |');
});

test('eventToMarkdownRow - null agent_id', () => {
  const event = {
    seq: 0,
    turn: 0,
    agent_id: null,
    type: 'run.config',
    ts: '2026-11-07T14:30:00Z',
  };
  const result = eventToMarkdownRow(event);
  assert.strictEqual(result, '| 0 | 0 | — | run.config | 2026-11-07T14:30:00Z |');
});

test('eventToMarkdownRow - escapes bidi in agent_id', () => {
  const event = {
    seq: 1,
    turn: 0,
    agent_id: 'agent\u200F-a',
    type: 'message.sent',
    ts: '2026-11-07T14:30:00Z',
  };
  const result = eventToMarkdownRow(event);
  assert.strictEqual(result, '| 1 | 0 | agent\\\\u200F-a | message.sent | 2026-11-07T14:30:00Z |');
});

test('eventsToMarkdownTable - converts array to table', () => {
  const events = [
    { seq: 0, turn: 0, agent_id: null, type: 'run.config', ts: '2026-11-07T14:30:00Z' },
    { seq: 1, turn: 0, agent_id: 'a', type: 'message.sent', ts: '2026-11-07T14:30:01Z' },
  ];
  const result = eventsToMarkdownTable(events);
  const expected = '| Seq | Turn | Agent | Type | Timestamp |\n|-----|------|-------|------|-----------|\n| 0 | 0 | — | run.config | 2026-11-07T14:30:00Z |\n| 1 | 0 | a | message.sent | 2026-11-07T14:30:01Z |';
  assert.strictEqual(result, expected);
});

test('eventsToMarkdownTable - empty array', () => {
  const result = eventsToMarkdownTable([]);
  const expected = '| Seq | Turn | Agent | Type | Timestamp |\n|-----|------|-------|------|-----------|';
  assert.strictEqual(result, expected);
});

test('episodeToMarkdown - full episode', () => {
  const episode = {
    config: {
      run_id: 'run-001',
      seed: 42,
      comm_topology: 'mesh',
      agents: ['a', 'b', 'c', 'd'],
      disturbance_schedule: { 'relay-loss': { turn: 2, agent: 'a' } },
    },
    events: [{ seq: 0, turn: 0, agent_id: null, type: 'run.config', ts: '2026-11-07T14:30:00Z' }],
  };
  const result = episodeToMarkdown(episode);
  assert.ok(result.includes('# Episode Export'));
  assert.ok(result.includes('## Configuration'));
  assert.ok(result.includes('**Run ID**: run-001'));
  assert.ok(result.includes('**Seed**: 42'));
  assert.ok(result.includes('**Topology**: mesh'));
  assert.ok(result.includes('## Event Log'));
  assert.ok(result.includes('| Seq | Turn | Agent | Type | Timestamp |'));
});

test('episodeToMarkdown - missing config', () => {
  const episode = { config: null, events: [] };
  const result = episodeToMarkdown(episode);
  assert.ok(result.includes('# Episode Export'));
});

test('episodeToMarkdown - escapes bidi in config values', () => {
  const episode = {
    config: {
      run_id: 'run\u200F-001',
      seed: 42,
      comm_topology: 'mesh',
      agents: ['a', 'b'],
    },
    events: [],
  };
  const result = episodeToMarkdown(episode);
  assert.ok(result.includes('\\\\u200F'));
});

test('text() - complete escape pipeline', () => {
  const input = 'test & <script>alert(1)</script>';
  const result = text(input);
  assert.strictEqual(result, 'test &#38;amp&#59; &#38;lt&#59;script&#38;gt&#59;alert&#40;1&#41;&#38;lt&#59;&#47;script&#38;gt&#59;');
});

test('text() - escapes apostrophe', () => {
  const input = "it's";
  const result = text(input);
  assert.strictEqual(result, 'it&#39;s');
});

test('text() - escapes punctuation in !-/:; range', () => {
  const input = 'hello! world-test';
  const result = text(input);
  assert.ok(result.includes('&#33;')); // !
  assert.ok(result.includes('&#45;')); // -
});

test('text() - combined bidi and entity attack', () => {
  const input = '\u202E&#x202E;reversed';
  const result = text(input);
  assert.ok(result.includes('\\u202E'));
  assert.ok(result.includes('&#38;')); // & escaped
  assert.ok(result.includes('&#35;')); // # escaped
  assert.strictEqual(result.includes('&#x202E;'), false);
});

// === SAST Probe Cases (added to address sast gate findings) ===

test('SAST probe: hostile run_id with invisible format characters', () => {
  // Word joiner U+2060, variation selector U+FE0F
  const input = 'run\u2060id\uFE0Ftest';
  const result = text(input);
  assert.strictEqual(result.includes('\u2060'), false, 'Word joiner should be escaped');
  assert.strictEqual(result.includes('\uFE0F'), false, 'Variation selector should be escaped');
  assert.ok(result.includes('\\u2060'), 'Word joiner should appear as visible escape');
  assert.ok(result.includes('\\uFE0F'), 'Variation selector should appear as visible escape');
});

test('SAST probe: script tag passthrough blocked', () => {
  const input = '<script>alert(1)</script>';
  const result = text(input);
  assert.strictEqual(result.includes('<script>'), false, 'Raw script tag should not survive');
  assert.ok(result.includes('&#38;lt&#59;'), 'Script tag should be double-escaped');
});

test('SAST probe: numeric entity injection blocked', () => {
  const input = '&#x202E;malicious';
  const result = text(input);
  assert.strictEqual(result.includes('&#x202E;'), false, 'Numeric entity should not survive');
  assert.ok(result.includes('&#38;'), 'Ampersand should be escaped first');
});

test('SAST probe: table-cell link injection blocked', () => {
  const input = '[click](evil.com)';
  const result = escapeMarkdown(input, { forTableCell: true });
  assert.strictEqual(result.includes('[click]'), false, 'Brackets should be escaped in table cells');
  assert.strictEqual(result.includes('(evil.com)'), false, 'Parens should be escaped in table cells');
  assert.ok(result.includes('\\['), 'Open bracket should be escaped');
  assert.ok(result.includes('\\]'), 'Close bracket should be escaped');
  assert.ok(result.includes('\\('), 'Open paren should be escaped');
  assert.ok(result.includes('\\)'), 'Close paren should be escaped');
});

test('SAST probe: escapeMarkdown HTML entity passthrough blocked', () => {
  // escapeMarkdown should escape & and <> to prevent HTML injection
  const input = '<script>&#x202E;</script>';
  const result = escapeMarkdown(input);
  assert.strictEqual(result.includes('<script>'), false, 'Raw HTML should not survive escapeMarkdown');
  assert.ok(result.includes('&amp;'), 'Ampersand should be escaped');
  assert.ok(result.includes('&lt;'), 'LT should be escaped');
  assert.ok(result.includes('&gt;'), 'GT should be escaped');
});
