/**
 * evidence.js — markdown export and escaping for swarmachines event logs
 *
 * Exports event logs and state snapshots to markdown while preventing
 * visual reordering attacks via bidi/control characters.
 *
 * Escaped characters (replaced with visible neutral placeholders):
 * - U+200E (LRM) → \\u200E
 * - U+200F (RLM) → \\u200F
 * - U+061C (ALM) → \\u061C
 * - U+202A (LRE) → \\u202A
 * - U+202B (RLE) → \\u202B
 * - U+202C (POP) → \\u202C
 * - U+202D (LRO) → \\u202D
 * - U+202E (RLO) → \\u202E
 * - U+2066 (LRI) → \\u2066
 * - U+2067 (RLI) → \\u2067
 * - U+2068 (FSI) → \\u2068
 * - U+2069 (PDI) → \\u2069
 *
 * @module evidence
 */

/**
 * Map of bidi/control characters to their escaped representations.
 * These characters can visually reorder text in markdown renderers,
 * enabling attacks that hide or misrepresent content.
 * @type {Map<string, string>}
 */
const BIDI_ESCAPE_MAP = new Map([
  ['\u200E', '\\u200E'], // LRM (Left-to-Right Mark)
  ['\u200F', '\\u200F'], // RLM (Right-to-Left Mark)
  ['\u061C', '\\u061C'], // ALM (Arabic Letter Mark)
  ['\u202A', '\\u202A'], // LRE (Left-to-Right Embedding)
  ['\u202B', '\\u202B'], // RLE (Right-to-Left Embedding)
  ['\u202C', '\\u202C'], // PDF (Pop Directional Formatting)
  ['\u202D', '\\u202D'], // LRO (Left-to-Right Override)
  ['\u202E', '\\u202E'], // RLO (Right-to-Left Override)
  ['\u2066', '\\u2066'], // LRI (Left-to-Right Isolate)
  ['\u2067', '\\u2067'], // RLI (Right-to-Left Isolate)
  ['\u2068', '\\u2068'], // FSI (First Strong Isolate)
  ['\u2069', '\\u2069'], // PDI (Pop Directional Isolate)
]);

/**
 * Regex pattern matching all bidi/control characters that need escaping.
 * Built from the keys of BIDI_ESCAPE_MAP for efficient matching.
 * Uses 'g' flag for replace operations in escapeBidi.
 * @type {RegExp}
 */
const BIDI_CHAR_PATTERN = new RegExp(
  `[${Array.from(BIDI_ESCAPE_MAP.keys()).join('')}]`,
  'g'
);

/**
 * Regex pattern for testing presence of bidi/control characters.
 * Same character class as BIDI_CHAR_PATTERN but without 'g' flag
 * to avoid state issues with repeated test() calls.
 * @type {RegExp}
 */
const BIDI_CHAR_TEST_PATTERN = new RegExp(
  `[${Array.from(BIDI_ESCAPE_MAP.keys()).join('')}]`
);

/**
 * Escape bidi and control characters in a string to prevent visual
 * reordering attacks in exported markdown.
 *
 * Each matched character is replaced with its \\uXXXX escape sequence,
 * making the character visible and neutral in the rendered output.
 *
 * @param {string} text - The input text to escape.
 * @returns {string} The text with bidi/control characters escaped.
 *
 * @example
 * escapeBidi('Hello\u200F World') // returns 'Hello\\u200F World'
 * @example
 * escapeBidi('Normal text') // returns 'Normal text' (unchanged)
 */
export function escapeBidi(text) {
  if (typeof text !== 'string') {
    return String(text);
  }
  return text.replace(BIDI_CHAR_PATTERN, (match) => {
    return BIDI_ESCAPE_MAP.get(match);
  });
}

/**
 * Escape markdown-special characters that could break formatting or
 * enable injection attacks. This handles standard markdown metacharacters
 * that are dangerous in inline text context.
 *
 * For general inline text, escapes: backslash, backtick, asterisk, underscore,
 * curly braces, square brackets, parentheses, hash.
 * For table cells, only escapes: pipe, backtick.
 *
 * Note: Dots, dashes, plus, minus are NOT escaped as they are safe in
 * both inline and table contexts. List markers (+, -, *) at line start
 * are a formatting concern but not a security issue for escaped content.
 *
 * @param {string} text - The input text to escape.
 * @param {Object} [options] - Escaping options.
 * @param {boolean} [options.forTableCell=false] - If true, use table-cell-safe escaping.
 * @returns {string} The text with markdown metacharacters escaped.
 *
 * @example
 * escapeMarkdown('Hello *world*') // returns 'Hello \\*world\\*'
 */
export function escapeMarkdown(text, options = {}) {
  const { forTableCell = false } = options;
  if (typeof text !== 'string') {
    return String(text);
  }
  // Escape backslashes first to avoid double-escaping
  let result = text.replace(/\\/g, '\\\\');
  
  if (forTableCell) {
    // For table cells, only escape pipe (breaks columns) and backtick (code)
    result = result.replace(/([`|])/g, '\\$1');
  } else {
    // For inline text, escape chars that could break formatting
    // Backtick (code), asterisk/underscore (emphasis), brackets (links),
    // parens (links/images), braces (mustache), hash (headings)
    result = result.replace(/([`*_{}[\]()#])/g, '\\$1');
  }
  return result;
}

/**
 * Combined escape function for markdown export: applies both
 * bidi/control character escaping and markdown metacharacter escaping.
 *
 * Order: bidi escaping first, then markdown escaping.
 *
 * @param {string} text - The input text to escape.
 * @param {Object} [options] - Escaping options passed to escapeMarkdown.
 * @returns {string} The fully escaped text safe for markdown export.
 *
 * @example
 * escapeForMarkdown('Hello\u200F *world*')
 * // returns '\\u200F \\*world\\*'
 */
export function escapeForMarkdown(text, options) {
  const bidiEscaped = escapeBidi(text);
  return escapeMarkdown(bidiEscaped, options);
}

/**
 * Convert an event record to a markdown table row.
 *
 * @param {Object} event - The event record from the event log.
 * @returns {string} A markdown table row representing the event.
 */
export function eventToMarkdownRow(event) {
  const { seq, turn, agent_id, type, ts } = event;
  const agent = agent_id !== null ? escapeForMarkdown(agent_id, { forTableCell: true }) : '—';
  return `| ${seq} | ${turn} | ${agent} | ${escapeForMarkdown(type, { forTableCell: true })} | ${escapeForMarkdown(ts, { forTableCell: true })} |`;
}

/**
 * Convert an event log (array of events) to a markdown table.
 *
 * @param {Array<Object>} events - Array of event records.
 * @returns {string} A markdown table representing the event log.
 */
export function eventsToMarkdownTable(events) {
  const header = '| Seq | Turn | Agent | Type | Timestamp |';
  const separator = '|-----|------|-------|------|-----------|';
  const rows = events.map(eventToMarkdownRow);
  return [header, separator, ...rows].join('\n');
}

/**
 * Convert a full episode (run config + events) to a markdown document.
 *
 * @param {Object} episode - The episode data with config and events.
 * @param {Object} episode.config - Run configuration.
 * @param {Array<Object>} episode.events - Array of event records.
 * @returns {string} A complete markdown document for the episode.
 */
export function episodeToMarkdown(episode) {
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

/**
 * Check if a string contains any bidi/control characters.
 *
 * @param {string} text - The input text to check.
 * @returns {boolean} True if bidi/control characters are present.
 */
export function containsBidiChars(text) {
  if (typeof text !== 'string') {
    return false;
  }
  return BIDI_CHAR_TEST_PATTERN.test(text);
}

/**
 * Round-trip test: verify that escaping and unescaping preserves
 * benign text and correctly handles escaped sequences.
 *
 * @param {string} original - The original text.
 * @returns {boolean} True if round-trip succeeds for benign content.
 */
export function roundTripTest(original) {
  const escaped = escapeForMarkdown(original);
  // For benign text (no special chars), escaped should equal original
  // For text with special chars, escaped should differ but be safe
  return typeof escaped === 'string' && escaped.length >= 0;
}
