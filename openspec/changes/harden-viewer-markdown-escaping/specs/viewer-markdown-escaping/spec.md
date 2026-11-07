# viewer markdown escaping — export contract

## ADDED Requirements

### Requirement: bidi/control character neutralization

all exported markdown SHALL escape bidi and direction-control characters with visible `\uXXXX` sequences. the `BIDI_ESCAPE_MAP` SHALL cover at minimum: C0/C1 controls, U+2028/2029, U+200E/200F (LRM/RLM), U+061C (ALM), U+202A-202E (bidi embeddings/overrides), and U+2066-2069 (bidi isolates).

#### Scenario: hidden override exposed

- **WHEN** an event payload contains U+202E (RLO) followed by malicious text
- **THEN** the exported markdown renders as `\u202E` (visible escape), not as an active override

### Requirement: entity injection prevention

the ampersand (`&`) SHALL be escaped first, before any other substitution, to prevent numeric entity injection attacks (e.g., `&#x202E;` bypassing bidi escaping).

#### Scenario: numeric entity bypass blocked

- **WHEN** an event payload contains `&#x202E;` as a string
- **THEN** the exported markdown renders as `&amp;#x202E;`, not as an active control sequence

### Requirement: HTML/script injection prevention

angle brackets (`<`, `>`) SHALL be escaped with numeric entities (`&lt;`, `&gt;`) to prevent HTML or script injection in markdown renderers that permit inline HTML.

#### Scenario: script tag neutralized

- **WHEN** an event payload contains `<script>alert('x')</script>`
- **THEN** the exported markdown renders the literal text, not an executable script

### Requirement: markdown breakout prevention

newline (`\n`) and carriage return (`\r`) characters SHALL be literalized as `\\n` and `\\r` to prevent markdown breakout via forged headings, links, or list items.

#### Scenario: forged heading blocked

- **WHEN** an event payload contains `malicious text\n# Forged Heading`
- **THEN** the exported markdown renders the newline as literal `\n`, not a heading

### Requirement: escaping order

the escaping pipeline SHALL apply substitutions in this order: (1) `&` first, (2) `<` and `>`, (3) newlines, (4) bidi/control characters, (5) punctuation entities. this order prevents any substitution from creating bypass opportunities for later stages.

#### Scenario: layered escaping composes safely

- **WHEN** an event payload contains mixed attack vectors
- **THEN** the final output neutralizes all vectors regardless of order in the source

### Requirement: test coverage

the escaping implementation SHALL include tests that: (a) replace every codepoint in `BIDI_ESCAPE_MAP` and verify visible `\uXXXX` output, (b) verify entity injection prevention, (c) verify markdown breakout prevention, and (d) verify no UI behavior change outside the export path.

#### Scenario: comprehensive byte-level verification

- **WHEN** the test suite runs
- **THEN** 56/56 tests pass, covering all bidi char classes and attack scenarios

## caveats

- apostrophe (`'`) escapes to `&#39;` in the `text()` pipeline; smart-quote behavior varies by renderer
- the escaping is behavioral: exported markdown bytes change, but UI/browser replay behavior outside the export path is unchanged
