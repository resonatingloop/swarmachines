# harden viewer markdown escaping (swarmachines-m04)

## why

invisible bidi and direction-control characters (LRM/RLM, ALM, LRE/RLE/LRO/RLO, isolates) can render misleadingly or smuggle content in exported evidence markdown. a malicious actor can craft event payloads that appear to say one thing while containing hidden directives that reorder or hide text in markdown renderers. the exported evidence packet must neutralize these attacks at the export boundary.

## what changes

- exported markdown escaping: `&` escaped first to prevent numeric entity injection (`&#x202E;` bypass)
- `<` and `>` escaped with numeric entities to prevent HTML/script injection
- newlines (`\n`, `\r`) literalized to prevent markdown breakout via forged headings/links
- `BIDI_ESCAPE_MAP` replacement of 82+ control/bidi codepoints with visible ASCII `\uXXXX` escapes:
  - C0 controls (0x00-0x1F except tab)
  - DEL and C1 controls (0x7F-0x9F)
  - U+2028/2029 (line/paragraph separators)
  - U+200E/200F (LRM/RLM), U+061C (ALM)
  - U+202A-202E (bidi embeddings/overrides)
  - U+2066-2069 (bidi isolates)
  - optional: U+200B/200C/200D (ZWJ/ZWNJ/ZWSP), U+00AD (SHY), U+FEFF (BOM)
- `escapeMarkdown()` helper for general inline text and table-cell modes
- `text()` function applies full escaping pipeline to all config.seed and string fields in markdown output

## caveats

- apostrophe normalization: `'` is not escaped; markdown renderers vary in smart-quote behavior
- the escape is behavioral: exported bytes change, but UI behavior outside the export path is unchanged

## how verified

- byte-level probe: test replaces all mapped codepoints and asserts visible `\uXXXX` output
- 46/46 node test suite (`evidence.test.js`) covering all bidi char classes
- no UI behavior change outside the export path (browser replay unaffected)
- verifier gate: escaping verified byte-level (PR #16)

## out of scope

- model-side input sanitization (producer responsibility)
- UI rendering hardening (separate viewer concern)

## acceptance

requirements verified against the test suite; owner accepts before archival.
