# tasks — harden-viewer-markdown-escaping

- [x] 1. implement `BIDI_ESCAPE_MAP` with 82+ control/bidi codepoints (C0/C1, U+2028/2029, LRM/RLM/ALM, embeddings/overrides/isolates, optional ZWJ/ZWNJ/ZWSP/SHY/BOM)
- [x] 2. implement `escapeBidi()` function replacing mapped chars with visible `\uXXXX` escapes
- [x] 3. implement `escapeMarkdown()` helper for inline text and table-cell modes
- [x] 4. implement `text()` function with full escaping pipeline: `&` first, then `<`/`>`, then newlines, then bidi, then punctuation entities
- [x] 5. apply `text()` to all config.seed and string fields in `markdown()` output
- [x] 6. implement 46-test suite (`evidence.test.js`) covering all bidi char classes and attack scenarios
- [x] 7. verify byte-level: tests replace all mapped codepoints and assert visible `\uXXXX` output
- [x] 8. verify no UI behavior change outside the export path (browser replay unaffected)
- [ ] 9. after owner acceptance: update STATUS.md and archive this change
