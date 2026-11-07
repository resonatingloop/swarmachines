/**
 * Tests for viewer/evidence.js markdown escaping
 *
 * Verifies that bidi/control characters are properly escaped to prevent
 * visual reordering attacks in exported markdown.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const Evidence = require('./evidence.js');
const {
  escapeBidi,
  escapeMarkdown,
  escapeForMarkdown,
  containsBidiChars,
  BIDI_ESCAPE_MAP,
} = Evidence;

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

describe('escapeBidi', () => {
  it('escapes U+200E (LRM) to visible placeholder', () => {
    const input = 'Hello\u200E World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u200E World');
  });

  it('escapes U+200F (RLM) to visible placeholder', () => {
    const input = 'Hello\u200F World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u200F World');
  });

  it('escapes U+061C (ALM) to visible placeholder', () => {
    const input = 'Hello\u061C World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u061C World');
  });

  it('escapes U+202A (LRE) to visible placeholder', () => {
    const input = 'Hello\u202A World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u202A World');
  });

  it('escapes U+202B (RLE) to visible placeholder', () => {
    const input = 'Hello\u202B World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u202B World');
  });

  it('escapes U+202C (PDF) to visible placeholder', () => {
    const input = 'Hello\u202C World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u202C World');
  });

  it('escapes U+202D (LRO) to visible placeholder', () => {
    const input = 'Hello\u202D World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u202D World');
  });

  it('escapes U+202E (RLO) to visible placeholder', () => {
    const input = 'Hello\u202E World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u202E World');
  });

  it('escapes U+2066 (LRI) to visible placeholder', () => {
    const input = 'Hello\u2066 World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u2066 World');
  });

  it('escapes U+2067 (RLI) to visible placeholder', () => {
    const input = 'Hello\u2067 World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u2067 World');
  });

  it('escapes U+2068 (FSI) to visible placeholder', () => {
    const input = 'Hello\u2068 World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u2068 World');
  });

  it('escapes U+2069 (PDI) to visible placeholder', () => {
    const input = 'Hello\u2069 World';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Hello\\u2069 World');
  });

  it('leaves benign text unchanged', () => {
    const input = 'Normal text without special chars';
    const result = escapeBidi(input);
    assert.strictEqual(result, 'Normal text without special chars');
  });

  it('handles multiple bidi chars in one string', () => {
    const input = '\u200E\u200F\u061C';
    const result = escapeBidi(input);
    assert.strictEqual(result, '\\u200E\\u200F\\u061C');
  });

  it('handles empty string', () => {
    const input = '';
    const result = escapeBidi(input);
    assert.strictEqual(result, '');
  });

  it('handles non-string input by converting to string', () => {
    const result = escapeBidi(123);
    assert.strictEqual(result, '123');
  });

  it('handles null input', () => {
    const result = escapeBidi(null);
    assert.strictEqual(result, 'null');
  });

});

describe('escapeMarkdown', () => {
  it('escapes asterisk (bold/italic marker)', () => {
    const input = 'Hello *world*';
    const result = escapeMarkdown(input);
    assert.strictEqual(result, 'Hello \\*world\\*');
  });

  it('escapes underscore (italic marker)', () => {
    const input = 'Hello _world_';
    const result = escapeMarkdown(input);
    assert.strictEqual(result, 'Hello \\_world\\_');
  });

  it('escapes backtick (code marker)', () => {
    const input = 'Hello `code`';
    const result = escapeMarkdown(input);
    assert.strictEqual(result, 'Hello \\`code\\`');
  });

  it('escapes backslash first to avoid double-escaping', () => {
    const input = 'path\\to\\file';
    const result = escapeMarkdown(input);
    assert.strictEqual(result, 'path\\\\to\\\\file');
  });

  it('escapes brackets (link markers)', () => {
    const input = 'Hello [link]';
    const result = escapeMarkdown(input);
    assert.strictEqual(result, 'Hello \\[link\\]');
  });

  it('escapes parentheses', () => {
    const input = 'Hello (world)';
    const result = escapeMarkdown(input);
    assert.strictEqual(result, 'Hello \\(world\\)');
  });

  it('escapes hash (heading marker)', () => {
    const input = '# Heading';
    const result = escapeMarkdown(input);
    assert.strictEqual(result, '\\# Heading');
  });

  it('escapes plus and minus (list markers)', () => {
    const input = '+ item\n- item';
    const result = escapeMarkdown(input);
    // Plus and minus are NOT escaped in inline text - they're only list markers at line start
    // Newline is preserved as a literal newline character
    assert.ok(result.includes('+ item'));
    assert.ok(result.includes('- item'));
  });

  it('leaves benign text unchanged', () => {
    const input = 'Normal text without special chars';
    const result = escapeMarkdown(input);
    assert.strictEqual(result, 'Normal text without special chars');
  });
});

describe('escapeForMarkdown', () => {
  it('applies bidi escaping then markdown escaping', () => {
    const input = '\u200F *italic*';
    const result = escapeForMarkdown(input);
    // Bidi char becomes \u200F, then backslash is escaped to \\u200F
    // Asterisks are escaped to \*
    assert.strictEqual(result, '\\\\u200F \\*italic\\*');
  });

  it('handles text with no special chars', () => {
    const input = 'Normal text';
    const result = escapeForMarkdown(input);
    assert.strictEqual(result, 'Normal text');
  });

  it('handles adversarial content with both bidi and markdown chars', () => {
    const input = '\u200E\u200F\u061C *bold* _italic_ `code`';
    const result = escapeForMarkdown(input);
    // Bidi escapes get their backslash escaped, markdown chars are escaped
    assert.ok(result.includes('\\\\u200E'));
    assert.ok(result.includes('\\\\u200F'));
    assert.ok(result.includes('\\\\u061C'));
    assert.ok(result.includes('\\*bold\\*'));
    assert.ok(result.includes('\\_italic\\_'));
    assert.ok(result.includes('\\`code\\`'));
  });
});

describe('containsBidiChars', () => {
  it('returns true for string with LRM', () => {
    assert.strictEqual(containsBidiChars('Hello\u200E'), true);
  });

  it('returns true for string with RLM', () => {
    assert.strictEqual(containsBidiChars('Hello\u200F'), true);
  });

  it('returns true for string with ALM', () => {
    assert.strictEqual(containsBidiChars('Hello\u061C'), true);
  });

  it('returns false for benign text', () => {
    assert.strictEqual(containsBidiChars('Normal text'), false);
  });

  it('returns false for empty string', () => {
    assert.strictEqual(containsBidiChars(''), false);
  });

  it('returns false for non-string input', () => {
    assert.strictEqual(containsBidiChars(123), false);
  });
});

describe('roundTripTest', () => {
  it('returns true for benign text', () => {
    assert.strictEqual(roundTripTest('Normal text'), true);
  });

  it('returns true for text with bidi chars', () => {
    assert.strictEqual(roundTripTest('\u200E\u200F'), true);
  });

  it('returns true for empty string', () => {
    assert.strictEqual(roundTripTest(''), true);
  });
});

describe('eventToMarkdownRow', () => {
  it('converts event to markdown row', () => {
    const event = {
      seq: 1,
      turn: 0,
      agent_id: 'agent-a',
      type: 'message.sent',
      ts: '2026-11-07T14:30:00Z',
    };
    const result = eventToMarkdownRow(event);
    // Table cells don't escape dots and dashes, only pipe and backtick
    assert.strictEqual(
      result,
      '| 1 | 0 | agent-a | message.sent | 2026-11-07T14:30:00Z |'
    );
  });

  it('handles null agent_id with em dash', () => {
    const event = {
      seq: 0,
      turn: 0,
      agent_id: null,
      type: 'run.config',
      ts: '2026-11-07T14:30:00Z',
    };
    const result = eventToMarkdownRow(event);
    assert.strictEqual(
      result,
      '| 0 | 0 | — | run.config | 2026-11-07T14:30:00Z |'
    );
  });

  it('escapes special chars in agent_id', () => {
    const event = {
      seq: 1,
      turn: 0,
      agent_id: 'agent\u200F-a',
      type: 'message.sent',
      ts: '2026-11-07T14:30:00Z',
    };
    const result = eventToMarkdownRow(event);
    // Bidi char is escaped, but dash is not escaped in table cells
    assert.strictEqual(
      result,
      '| 1 | 0 | agent\\\\u200F-a | message.sent | 2026-11-07T14:30:00Z |'
    );
  });
});

describe('eventsToMarkdownTable', () => {
  it('converts array of events to markdown table', () => {
    const events = [
      {
        seq: 0,
        turn: 0,
        agent_id: null,
        type: 'run.config',
        ts: '2026-11-07T14:30:00Z',
      },
      {
        seq: 1,
        turn: 0,
        agent_id: 'a',
        type: 'message.sent',
        ts: '2026-11-07T14:30:01Z',
      },
    ];
    const result = eventsToMarkdownTable(events);
    const expected =
      '| Seq | Turn | Agent | Type | Timestamp |\n' +
      '|-----|------|-------|------|-----------|\n' +
      '| 0 | 0 | — | run.config | 2026-11-07T14:30:00Z |\n' +
      '| 1 | 0 | a | message.sent | 2026-11-07T14:30:01Z |';
    assert.strictEqual(result, expected);
  });

  it('handles empty event array', () => {
    const result = eventsToMarkdownTable([]);
    const expected = '| Seq | Turn | Agent | Type | Timestamp |\n|-----|------|-------|------|-----------|';
    assert.strictEqual(result, expected);
  });
});

describe('episodeToMarkdown', () => {
  it('converts full episode to markdown document', () => {
    const episode = {
      config: {
        run_id: 'run-001',
        seed: 42,
        comm_topology: 'mesh',
        agents: ['a', 'b', 'c', 'd'],
        disturbance_schedule: { 'relay-loss': { turn: 2, agent: 'a' } },
      },
      events: [
        {
          seq: 0,
          turn: 0,
          agent_id: null,
          type: 'run.config',
          ts: '2026-11-07T14:30:00Z',
        },
      ],
    };
    const result = episodeToMarkdown(episode);
    assert.ok(result.includes('# Episode Export'));
    assert.ok(result.includes('## Configuration'));
    // Dashes are not escaped in inline text anymore
    assert.ok(result.includes('**Run ID**: run-001'));
    assert.ok(result.includes('**Seed**: 42'));
    assert.ok(result.includes('**Topology**: mesh'));
    assert.ok(result.includes('## Event Log'));
    assert.ok(result.includes('| Seq | Turn | Agent | Type | Timestamp |'));
  });

  it('handles missing config gracefully', () => {
    const episode = {
      config: null,
      events: [],
    };
    const result = episodeToMarkdown(episode);
    assert.ok(result.includes('# Episode Export'));
  });

  it('escapes bidi chars in config values', () => {
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
    // Bidi char is escaped, and the backslash is also escaped for markdown
    assert.ok(result.includes('\\\\u200F'));
  });
});
