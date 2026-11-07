/* Derived evidence only. Original logs are required to inspect source payloads. */
'use strict';
const CompareEvidence = typeof module !== 'undefined' ? require('./comparison.js') : globalThis.Comparison;
const SCHEMA = 'swarmachines.evidence-packet.v1';
const VERSION = '1.0.0';
const MAX_BYTES = 2 * 1024 * 1024;
const CAVEATS = [
  'paired files are not a certified matched experiment; equal logged settings do not establish equal worlds, policies or generation controls.',
  'counts describe records, not unique messages, successful decisions, delivered freight or causal effects.',
  'selection may omit relevant turns; selected-turn summaries are not whole-run estimates.',
  'carried-forward observations retain their recorded age; missing records and missing turns are not evidence of no activity.',
  'source hashes establish byte identity only. original source files are required for raw evidence inspection.',
  'configuration is file-level context; cursor-scoped evidence remains bounded by each selected turn.',
  'no outcome or world-backed claim is established by this export.',
  "count vocabulary covers only the comparison model's named types; other event types remain in the source files.",
  'logged configuration and identifiers may contain producer-supplied sensitive content; this packet is not anonymized or certified safe to publish.'
];

/**
 * Map of bidi/control characters to their escaped representations.
 * These characters can visually reorder text in markdown renderers,
 * enabling attacks that hide or misrepresent content.
 * Includes: C0/C1 controls, U+2028/2029, bidi overrides/isolates/marks, ZWJ/ZWNJ/SHY/BOM,
 * invisible format characters (word joiners, annotation chars),
 * language tag plane (U+E0000-U+E007F, including 30 unassigned U+E0002-U+E001F),
 * variation selectors (U+FE00-FE0F and U+E0100-E01EF),
 * and musical formatting controls (U+1D173-U+1D17A).
 * @type {Map<string, string>}
 */
const BIDI_ESCAPE_MAP = new Map([
['\u0000', '\\u0000'],
  ['\u0001', '\\u0001'],
  ['\u0002', '\\u0002'],
  ['\u0003', '\\u0003'],
  ['\u0004', '\\u0004'],
  ['\u0005', '\\u0005'],
  ['\u0006', '\\u0006'],
  ['\u0007', '\\u0007'],
  ['\u0008', '\\u0008'],
  ['\u0009', '\\u0009'],
  ['\u000B', '\\u000B'],
  ['\u000C', '\\u000C'],
  ['\u000E', '\\u000E'],
  ['\u000F', '\\u000F'],
  ['\u0010', '\\u0010'],
  ['\u0011', '\\u0011'],
  ['\u0012', '\\u0012'],
  ['\u0013', '\\u0013'],
  ['\u0014', '\\u0014'],
  ['\u0015', '\\u0015'],
  ['\u0016', '\\u0016'],
  ['\u0017', '\\u0017'],
  ['\u0018', '\\u0018'],
  ['\u0019', '\\u0019'],
  ['\u001A', '\\u001A'],
  ['\u001B', '\\u001B'],
  ['\u001C', '\\u001C'],
  ['\u001D', '\\u001D'],
  ['\u001E', '\\u001E'],
  ['\u001F', '\\u001F'],
  ['\u007F', '\\u007F'],
  ['\u0080', '\\u0080'],
  ['\u0081', '\\u0081'],
  ['\u0082', '\\u0082'],
  ['\u0083', '\\u0083'],
  ['\u0084', '\\u0084'],
  ['\u0085', '\\u0085'],
  ['\u0086', '\\u0086'],
  ['\u0087', '\\u0087'],
  ['\u0088', '\\u0088'],
  ['\u0089', '\\u0089'],
  ['\u008A', '\\u008A'],
  ['\u008B', '\\u008B'],
  ['\u008C', '\\u008C'],
  ['\u008D', '\\u008D'],
  ['\u008E', '\\u008E'],
  ['\u008F', '\\u008F'],
  ['\u0090', '\\u0090'],
  ['\u0091', '\\u0091'],
  ['\u0092', '\\u0092'],
  ['\u0093', '\\u0093'],
  ['\u0094', '\\u0094'],
  ['\u0095', '\\u0095'],
  ['\u0096', '\\u0096'],
  ['\u0097', '\\u0097'],
  ['\u0098', '\\u0098'],
  ['\u0099', '\\u0099'],
  ['\u009A', '\\u009A'],
  ['\u009B', '\\u009B'],
  ['\u009C', '\\u009C'],
  ['\u009D', '\\u009D'],
  ['\u009E', '\\u009E'],
  ['\u009F', '\\u009F'],
  ['\u2028', '\\u2028'], // LS (Line Separator)
  ['\u2029', '\\u2029'], // PS (Paragraph Separator)
  ['\u200E', '\\u200E'], // LRM
  ['\u200F', '\\u200F'], // RLM
  ['\u061C', '\\u061C'], // ALM
  ['\u202A', '\\u202A'], // LRE
  ['\u202B', '\\u202B'], // RLE
  ['\u202C', '\\u202C'], // PDF
  ['\u202D', '\\u202D'], // LRO
  ['\u202E', '\\u202E'], // RLO
  ['\u2066', '\\u2066'], // LRI
  ['\u2067', '\\u2067'], // RLI
  ['\u2068', '\\u2068'], // FSI
  ['\u2069', '\\u2069'], // PDI
  ['\u200B', '\\u200B'], // ZWSP
  ['\u200C', '\\u200C'], // ZWNJ
  ['\u200D', '\\u200D'], // ZWJ
  ['\u00AD', '\\u00AD'], // SHY
  ['\uFEFF', '\\uFEFF'], // BOM/ZWNBSP
  ['\u2060', '\\u2060'], // Word Joiner
  ['\u2061', '\\u2061'], // Function Application
  ['\u2062', '\\u2062'], // Invisible Times
  ['\u2063', '\\u2063'], // Invisible Separator
  ['\u2064', '\\u2064'], // Invisible Plus
  ['\uFFF9', '\\uFFF9'], // Interlinear Annotation Anchor
  ['\uFFFA', '\\uFFFA'], // Interlinear Annotation Separator
  ['\uFFFB', '\\uFFFB'], // Interlinear Annotation Terminator
  [String.fromCodePoint(0x1D173), '\\uD834\\uDD73'], // Musical Symbol Begin Beam
  [String.fromCodePoint(0x1D174), '\\uD834\\uDD74'], // Musical Symbol End Beam
  [String.fromCodePoint(0x1D175), '\\uD834\\uDD75'], // Musical Symbol Begin Slur
  [String.fromCodePoint(0x1D176), '\\uD834\\uDD76'], // Musical Symbol End Slur
  [String.fromCodePoint(0x1D177), '\\uD834\\uDD77'], // Musical Symbol Begin Phrase
  [String.fromCodePoint(0x1D178), '\\uD834\\uDD78'], // Musical Symbol End Phrase
  [String.fromCodePoint(0x1D179), '\\uD834\\uDD79'], // Musical Symbol Begin Repeat
  [String.fromCodePoint(0x1D17A), '\\uD834\\uDD7A'], // Musical Symbol End Repeat
  [String.fromCodePoint(0xE0000), '\\uDB40\\uDC00'], // TAG
  [String.fromCodePoint(0xE0001), '\\uDB40\\uDC01'], // LANGUAGE TAG
  [String.fromCodePoint(0xE0002), '\\uDB40\\uDC02'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0003), '\\uDB40\\uDC03'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0004), '\\uDB40\\uDC04'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0005), '\\uDB40\\uDC05'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0006), '\\uDB40\\uDC06'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0007), '\\uDB40\\uDC07'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0008), '\\uDB40\\uDC08'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0009), '\\uDB40\\uDC09'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE000A), '\\uDB40\\uDC0A'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE000B), '\\uDB40\\uDC0B'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE000C), '\\uDB40\\uDC0C'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE000D), '\\uDB40\\uDC0D'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE000E), '\\uDB40\\uDC0E'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE000F), '\\uDB40\\uDC0F'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0010), '\\uDB40\\uDC10'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0011), '\\uDB40\\uDC11'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0012), '\\uDB40\\uDC12'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0013), '\\uDB40\\uDC13'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0014), '\\uDB40\\uDC14'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0015), '\\uDB40\\uDC15'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0016), '\\uDB40\\uDC16'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0017), '\\uDB40\\uDC17'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0018), '\\uDB40\\uDC18'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0019), '\\uDB40\\uDC19'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE001A), '\\uDB40\\uDC1A'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE001B), '\\uDB40\\uDC1B'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE001C), '\\uDB40\\uDC1C'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE001D), '\\uDB40\\uDC1D'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE001E), '\\uDB40\\uDC1E'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE001F), '\\uDB40\\uDC1F'], // TAG PLANE UNASSIGNED
  [String.fromCodePoint(0xE0020), '\\uDB40\\uDC20'], // TAG SPACE
  [String.fromCodePoint(0xE0021), '\\uDB40\\uDC21'], // TAG EXCLAMATION MARK
  [String.fromCodePoint(0xE0022), '\\uDB40\\uDC22'], // TAG QUOTATION MARK
  [String.fromCodePoint(0xE0023), '\\uDB40\\uDC23'], // TAG NUMBER SIGN
  [String.fromCodePoint(0xE0024), '\\uDB40\\uDC24'], // TAG DOLLAR SIGN
  [String.fromCodePoint(0xE0025), '\\uDB40\\uDC25'], // TAG PERCENT SIGN
  [String.fromCodePoint(0xE0026), '\\uDB40\\uDC26'], // TAG AMPERSAND
  [String.fromCodePoint(0xE0027), '\\uDB40\\uDC27'], // TAG APOSTROPHE
  [String.fromCodePoint(0xE0028), '\\uDB40\\uDC28'], // TAG LEFT PARENTHESIS
  [String.fromCodePoint(0xE0029), '\\uDB40\\uDC29'], // TAG RIGHT PARENTHESIS
  [String.fromCodePoint(0xE002A), '\\uDB40\\uDC2A'], // TAG ASTERISK
  [String.fromCodePoint(0xE002B), '\\uDB40\\uDC2B'], // TAG PLUS SIGN
  [String.fromCodePoint(0xE002C), '\\uDB40\\uDC2C'], // TAG COMMA
  [String.fromCodePoint(0xE002D), '\\uDB40\\uDC2D'], // TAG HYPHEN-MINUS
  [String.fromCodePoint(0xE002E), '\\uDB40\\uDC2E'], // TAG FULL STOP
  [String.fromCodePoint(0xE002F), '\\uDB40\\uDC2F'], // TAG SOLIDUS
  [String.fromCodePoint(0xE0030), '\\uDB40\\uDC30'], // TAG DIGIT ZERO
  [String.fromCodePoint(0xE0031), '\\uDB40\\uDC31'], // TAG DIGIT ONE
  [String.fromCodePoint(0xE0032), '\\uDB40\\uDC32'], // TAG DIGIT TWO
  [String.fromCodePoint(0xE0033), '\\uDB40\\uDC33'], // TAG DIGIT THREE
  [String.fromCodePoint(0xE0034), '\\uDB40\\uDC34'], // TAG DIGIT FOUR
  [String.fromCodePoint(0xE0035), '\\uDB40\\uDC35'], // TAG DIGIT FIVE
  [String.fromCodePoint(0xE0036), '\\uDB40\\uDC36'], // TAG DIGIT SIX
  [String.fromCodePoint(0xE0037), '\\uDB40\\uDC37'], // TAG DIGIT SEVEN
  [String.fromCodePoint(0xE0038), '\\uDB40\\uDC38'], // TAG DIGIT EIGHT
  [String.fromCodePoint(0xE0039), '\\uDB40\\uDC39'], // TAG DIGIT NINE
  [String.fromCodePoint(0xE003A), '\\uDB40\\uDC3A'], // TAG COLON
  [String.fromCodePoint(0xE003B), '\\uDB40\\uDC3B'], // TAG SEMICOLON
  [String.fromCodePoint(0xE003C), '\\uDB40\\uDC3C'], // TAG LESS-THAN SIGN
  [String.fromCodePoint(0xE003D), '\\uDB40\\uDC3D'], // TAG EQUALS SIGN
  [String.fromCodePoint(0xE003E), '\\uDB40\\uDC3E'], // TAG GREATER-THAN SIGN
  [String.fromCodePoint(0xE003F), '\\uDB40\\uDC3F'], // TAG QUESTION MARK
  [String.fromCodePoint(0xE0040), '\\uDB40\\uDC40'], // TAG COMMERCIAL AT
  [String.fromCodePoint(0xE0041), '\\uDB40\\uDC41'], // TAG LATIN CAPITAL LETTER A
  [String.fromCodePoint(0xE0042), '\\uDB40\\uDC42'], // TAG LATIN CAPITAL LETTER B
  [String.fromCodePoint(0xE0043), '\\uDB40\\uDC43'], // TAG LATIN CAPITAL LETTER C
  [String.fromCodePoint(0xE0044), '\\uDB40\\uDC44'], // TAG LATIN CAPITAL LETTER D
  [String.fromCodePoint(0xE0045), '\\uDB40\\uDC45'], // TAG LATIN CAPITAL LETTER E
  [String.fromCodePoint(0xE0046), '\\uDB40\\uDC46'], // TAG LATIN CAPITAL LETTER F
  [String.fromCodePoint(0xE0047), '\\uDB40\\uDC47'], // TAG LATIN CAPITAL LETTER G
  [String.fromCodePoint(0xE0048), '\\uDB40\\uDC48'], // TAG LATIN CAPITAL LETTER H
  [String.fromCodePoint(0xE0049), '\\uDB40\\uDC49'], // TAG LATIN CAPITAL LETTER I
  [String.fromCodePoint(0xE004A), '\\uDB40\\uDC4A'], // TAG LATIN CAPITAL LETTER J
  [String.fromCodePoint(0xE004B), '\\uDB40\\uDC4B'], // TAG LATIN CAPITAL LETTER K
  [String.fromCodePoint(0xE004C), '\\uDB40\\uDC4C'], // TAG LATIN CAPITAL LETTER L
  [String.fromCodePoint(0xE004D), '\\uDB40\\uDC4D'], // TAG LATIN CAPITAL LETTER M
  [String.fromCodePoint(0xE004E), '\\uDB40\\uDC4E'], // TAG LATIN CAPITAL LETTER N
  [String.fromCodePoint(0xE004F), '\\uDB40\\uDC4F'], // TAG LATIN CAPITAL LETTER O
  [String.fromCodePoint(0xE0050), '\\uDB40\\uDC50'], // TAG LATIN CAPITAL LETTER P
  [String.fromCodePoint(0xE0051), '\\uDB40\\uDC51'], // TAG LATIN CAPITAL LETTER Q
  [String.fromCodePoint(0xE0052), '\\uDB40\\uDC52'], // TAG LATIN CAPITAL LETTER R
  [String.fromCodePoint(0xE0053), '\\uDB40\\uDC53'], // TAG LATIN CAPITAL LETTER S
  [String.fromCodePoint(0xE0054), '\\uDB40\\uDC54'], // TAG LATIN CAPITAL LETTER T
  [String.fromCodePoint(0xE0055), '\\uDB40\\uDC55'], // TAG LATIN CAPITAL LETTER U
  [String.fromCodePoint(0xE0056), '\\uDB40\\uDC56'], // TAG LATIN CAPITAL LETTER V
  [String.fromCodePoint(0xE0057), '\\uDB40\\uDC57'], // TAG LATIN CAPITAL LETTER W
  [String.fromCodePoint(0xE0058), '\\uDB40\\uDC58'], // TAG LATIN CAPITAL LETTER X
  [String.fromCodePoint(0xE0059), '\\uDB40\\uDC59'], // TAG LATIN CAPITAL LETTER Y
  [String.fromCodePoint(0xE005A), '\\uDB40\\uDC5A'], // TAG LATIN CAPITAL LETTER Z
  [String.fromCodePoint(0xE005B), '\\uDB40\\uDC5B'], // TAG LEFT SQUARE BRACKET
  [String.fromCodePoint(0xE005C), '\\uDB40\\uDC5C'], // TAG REVERSE SOLIDUS
  [String.fromCodePoint(0xE005D), '\\uDB40\\uDC5D'], // TAG RIGHT SQUARE BRACKET
  [String.fromCodePoint(0xE005E), '\\uDB40\\uDC5E'], // TAG CIRCUMFLEX ACCENT
  [String.fromCodePoint(0xE005F), '\\uDB40\\uDC5F'], // TAG LOW LINE
  [String.fromCodePoint(0xE0060), '\\uDB40\\uDC60'], // TAG GRAVE ACCENT
  [String.fromCodePoint(0xE0061), '\\uDB40\\uDC61'], // TAG LATIN SMALL LETTER a
  [String.fromCodePoint(0xE0062), '\\uDB40\\uDC62'], // TAG LATIN SMALL LETTER b
  [String.fromCodePoint(0xE0063), '\\uDB40\\uDC63'], // TAG LATIN SMALL LETTER c
  [String.fromCodePoint(0xE0064), '\\uDB40\\uDC64'], // TAG LATIN SMALL LETTER d
  [String.fromCodePoint(0xE0065), '\\uDB40\\uDC65'], // TAG LATIN SMALL LETTER e
  [String.fromCodePoint(0xE0066), '\\uDB40\\uDC66'], // TAG LATIN SMALL LETTER f
  [String.fromCodePoint(0xE0067), '\\uDB40\\uDC67'], // TAG LATIN SMALL LETTER g
  [String.fromCodePoint(0xE0068), '\\uDB40\\uDC68'], // TAG LATIN SMALL LETTER h
  [String.fromCodePoint(0xE0069), '\\uDB40\\uDC69'], // TAG LATIN SMALL LETTER i
  [String.fromCodePoint(0xE006A), '\\uDB40\\uDC6A'], // TAG LATIN SMALL LETTER j
  [String.fromCodePoint(0xE006B), '\\uDB40\\uDC6B'], // TAG LATIN SMALL LETTER k
  [String.fromCodePoint(0xE006C), '\\uDB40\\uDC6C'], // TAG LATIN SMALL LETTER l
  [String.fromCodePoint(0xE006D), '\\uDB40\\uDC6D'], // TAG LATIN SMALL LETTER m
  [String.fromCodePoint(0xE006E), '\\uDB40\\uDC6E'], // TAG LATIN SMALL LETTER n
  [String.fromCodePoint(0xE006F), '\\uDB40\\uDC6F'], // TAG LATIN SMALL LETTER o
  [String.fromCodePoint(0xE0070), '\\uDB40\\uDC70'], // TAG LATIN SMALL LETTER p
  [String.fromCodePoint(0xE0071), '\\uDB40\\uDC71'], // TAG LATIN SMALL LETTER q
  [String.fromCodePoint(0xE0072), '\\uDB40\\uDC72'], // TAG LATIN SMALL LETTER r
  [String.fromCodePoint(0xE0073), '\\uDB40\\uDC73'], // TAG LATIN SMALL LETTER s
  [String.fromCodePoint(0xE0074), '\\uDB40\\uDC74'], // TAG LATIN SMALL LETTER t
  [String.fromCodePoint(0xE0075), '\\uDB40\\uDC75'], // TAG LATIN SMALL LETTER u
  [String.fromCodePoint(0xE0076), '\\uDB40\\uDC76'], // TAG LATIN SMALL LETTER v
  [String.fromCodePoint(0xE0077), '\\uDB40\\uDC77'], // TAG LATIN SMALL LETTER w
  [String.fromCodePoint(0xE0078), '\\uDB40\\uDC78'], // TAG LATIN SMALL LETTER x
  [String.fromCodePoint(0xE0079), '\\uDB40\\uDC79'], // TAG LATIN SMALL LETTER y
  [String.fromCodePoint(0xE007A), '\\uDB40\\uDC7A'], // TAG LATIN SMALL LETTER z
  [String.fromCodePoint(0xE007B), '\\uDB40\\uDC7B'], // TAG LEFT CURLY BRACKET
  [String.fromCodePoint(0xE007C), '\\uDB40\\uDC7C'], // TAG VERTICAL LINE
  [String.fromCodePoint(0xE007D), '\\uDB40\\uDC7D'], // TAG RIGHT CURLY BRACKET
  [String.fromCodePoint(0xE007E), '\\uDB40\\uDC7E'], // TAG TILDE
  [String.fromCodePoint(0xE007F), '\\uDB40\\uDC7F'], // TAG DELETE
  ['\uFE00', '\\uFE00'],
  ['\uFE01', '\\uFE01'],
  ['\uFE02', '\\uFE02'],
  ['\uFE03', '\\uFE03'],
  ['\uFE04', '\\uFE04'],
  ['\uFE05', '\\uFE05'],
  ['\uFE06', '\\uFE06'],
  ['\uFE07', '\\uFE07'],
  ['\uFE08', '\\uFE08'],
  ['\uFE09', '\\uFE09'],
  ['\uFE0A', '\\uFE0A'],
  ['\uFE0B', '\\uFE0B'],
  ['\uFE0C', '\\uFE0C'],
  ['\uFE0D', '\\uFE0D'],
  ['\uFE0E', '\\uFE0E'],
  ['\uFE0F', '\\uFE0F'],
  [String.fromCodePoint(0xE0100), '\\uDB40\\uDD00'],
  [String.fromCodePoint(0xE0101), '\\uDB40\\uDD01'],
  [String.fromCodePoint(0xE0102), '\\uDB40\\uDD02'],
  [String.fromCodePoint(0xE0103), '\\uDB40\\uDD03'],
  [String.fromCodePoint(0xE0104), '\\uDB40\\uDD04'],
  [String.fromCodePoint(0xE0105), '\\uDB40\\uDD05'],
  [String.fromCodePoint(0xE0106), '\\uDB40\\uDD06'],
  [String.fromCodePoint(0xE0107), '\\uDB40\\uDD07'],
  [String.fromCodePoint(0xE0108), '\\uDB40\\uDD08'],
  [String.fromCodePoint(0xE0109), '\\uDB40\\uDD09'],
  [String.fromCodePoint(0xE010A), '\\uDB40\\uDD0A'],
  [String.fromCodePoint(0xE010B), '\\uDB40\\uDD0B'],
  [String.fromCodePoint(0xE010C), '\\uDB40\\uDD0C'],
  [String.fromCodePoint(0xE010D), '\\uDB40\\uDD0D'],
  [String.fromCodePoint(0xE010E), '\\uDB40\\uDD0E'],
  [String.fromCodePoint(0xE010F), '\\uDB40\\uDD0F'],
  [String.fromCodePoint(0xE0110), '\\uDB40\\uDD10'],
  [String.fromCodePoint(0xE0111), '\\uDB40\\uDD11'],
  [String.fromCodePoint(0xE0112), '\\uDB40\\uDD12'],
  [String.fromCodePoint(0xE0113), '\\uDB40\\uDD13'],
  [String.fromCodePoint(0xE0114), '\\uDB40\\uDD14'],
  [String.fromCodePoint(0xE0115), '\\uDB40\\uDD15'],
  [String.fromCodePoint(0xE0116), '\\uDB40\\uDD16'],
  [String.fromCodePoint(0xE0117), '\\uDB40\\uDD17'],
  [String.fromCodePoint(0xE0118), '\\uDB40\\uDD18'],
  [String.fromCodePoint(0xE0119), '\\uDB40\\uDD19'],
  [String.fromCodePoint(0xE011A), '\\uDB40\\uDD1A'],
  [String.fromCodePoint(0xE011B), '\\uDB40\\uDD1B'],
  [String.fromCodePoint(0xE011C), '\\uDB40\\uDD1C'],
  [String.fromCodePoint(0xE011D), '\\uDB40\\uDD1D'],
  [String.fromCodePoint(0xE011E), '\\uDB40\\uDD1E'],
  [String.fromCodePoint(0xE011F), '\\uDB40\\uDD1F'],
  [String.fromCodePoint(0xE0120), '\\uDB40\\uDD20'],
  [String.fromCodePoint(0xE0121), '\\uDB40\\uDD21'],
  [String.fromCodePoint(0xE0122), '\\uDB40\\uDD22'],
  [String.fromCodePoint(0xE0123), '\\uDB40\\uDD23'],
  [String.fromCodePoint(0xE0124), '\\uDB40\\uDD24'],
  [String.fromCodePoint(0xE0125), '\\uDB40\\uDD25'],
  [String.fromCodePoint(0xE0126), '\\uDB40\\uDD26'],
  [String.fromCodePoint(0xE0127), '\\uDB40\\uDD27'],
  [String.fromCodePoint(0xE0128), '\\uDB40\\uDD28'],
  [String.fromCodePoint(0xE0129), '\\uDB40\\uDD29'],
  [String.fromCodePoint(0xE012A), '\\uDB40\\uDD2A'],
  [String.fromCodePoint(0xE012B), '\\uDB40\\uDD2B'],
  [String.fromCodePoint(0xE012C), '\\uDB40\\uDD2C'],
  [String.fromCodePoint(0xE012D), '\\uDB40\\uDD2D'],
  [String.fromCodePoint(0xE012E), '\\uDB40\\uDD2E'],
  [String.fromCodePoint(0xE012F), '\\uDB40\\uDD2F'],
  [String.fromCodePoint(0xE0130), '\\uDB40\\uDD30'],
  [String.fromCodePoint(0xE0131), '\\uDB40\\uDD31'],
  [String.fromCodePoint(0xE0132), '\\uDB40\\uDD32'],
  [String.fromCodePoint(0xE0133), '\\uDB40\\uDD33'],
  [String.fromCodePoint(0xE0134), '\\uDB40\\uDD34'],
  [String.fromCodePoint(0xE0135), '\\uDB40\\uDD35'],
  [String.fromCodePoint(0xE0136), '\\uDB40\\uDD36'],
  [String.fromCodePoint(0xE0137), '\\uDB40\\uDD37'],
  [String.fromCodePoint(0xE0138), '\\uDB40\\uDD38'],
  [String.fromCodePoint(0xE0139), '\\uDB40\\uDD39'],
  [String.fromCodePoint(0xE013A), '\\uDB40\\uDD3A'],
  [String.fromCodePoint(0xE013B), '\\uDB40\\uDD3B'],
  [String.fromCodePoint(0xE013C), '\\uDB40\\uDD3C'],
  [String.fromCodePoint(0xE013D), '\\uDB40\\uDD3D'],
  [String.fromCodePoint(0xE013E), '\\uDB40\\uDD3E'],
  [String.fromCodePoint(0xE013F), '\\uDB40\\uDD3F'],
  [String.fromCodePoint(0xE0140), '\\uDB40\\uDD40'],
  [String.fromCodePoint(0xE0141), '\\uDB40\\uDD41'],
  [String.fromCodePoint(0xE0142), '\\uDB40\\uDD42'],
  [String.fromCodePoint(0xE0143), '\\uDB40\\uDD43'],
  [String.fromCodePoint(0xE0144), '\\uDB40\\uDD44'],
  [String.fromCodePoint(0xE0145), '\\uDB40\\uDD45'],
  [String.fromCodePoint(0xE0146), '\\uDB40\\uDD46'],
  [String.fromCodePoint(0xE0147), '\\uDB40\\uDD47'],
  [String.fromCodePoint(0xE0148), '\\uDB40\\uDD48'],
  [String.fromCodePoint(0xE0149), '\\uDB40\\uDD49'],
  [String.fromCodePoint(0xE014A), '\\uDB40\\uDD4A'],
  [String.fromCodePoint(0xE014B), '\\uDB40\\uDD4B'],
  [String.fromCodePoint(0xE014C), '\\uDB40\\uDD4C'],
  [String.fromCodePoint(0xE014D), '\\uDB40\\uDD4D'],
  [String.fromCodePoint(0xE014E), '\\uDB40\\uDD4E'],
  [String.fromCodePoint(0xE014F), '\\uDB40\\uDD4F'],
  [String.fromCodePoint(0xE0150), '\\uDB40\\uDD50'],
  [String.fromCodePoint(0xE0151), '\\uDB40\\uDD51'],
  [String.fromCodePoint(0xE0152), '\\uDB40\\uDD52'],
  [String.fromCodePoint(0xE0153), '\\uDB40\\uDD53'],
  [String.fromCodePoint(0xE0154), '\\uDB40\\uDD54'],
  [String.fromCodePoint(0xE0155), '\\uDB40\\uDD55'],
  [String.fromCodePoint(0xE0156), '\\uDB40\\uDD56'],
  [String.fromCodePoint(0xE0157), '\\uDB40\\uDD57'],
  [String.fromCodePoint(0xE0158), '\\uDB40\\uDD58'],
  [String.fromCodePoint(0xE0159), '\\uDB40\\uDD59'],
  [String.fromCodePoint(0xE015A), '\\uDB40\\uDD5A'],
  [String.fromCodePoint(0xE015B), '\\uDB40\\uDD5B'],
  [String.fromCodePoint(0xE015C), '\\uDB40\\uDD5C'],
  [String.fromCodePoint(0xE015D), '\\uDB40\\uDD5D'],
  [String.fromCodePoint(0xE015E), '\\uDB40\\uDD5E'],
  [String.fromCodePoint(0xE015F), '\\uDB40\\uDD5F'],
  [String.fromCodePoint(0xE0160), '\\uDB40\\uDD60'],
  [String.fromCodePoint(0xE0161), '\\uDB40\\uDD61'],
  [String.fromCodePoint(0xE0162), '\\uDB40\\uDD62'],
  [String.fromCodePoint(0xE0163), '\\uDB40\\uDD63'],
  [String.fromCodePoint(0xE0164), '\\uDB40\\uDD64'],
  [String.fromCodePoint(0xE0165), '\\uDB40\\uDD65'],
  [String.fromCodePoint(0xE0166), '\\uDB40\\uDD66'],
  [String.fromCodePoint(0xE0167), '\\uDB40\\uDD67'],
  [String.fromCodePoint(0xE0168), '\\uDB40\\uDD68'],
  [String.fromCodePoint(0xE0169), '\\uDB40\\uDD69'],
  [String.fromCodePoint(0xE016A), '\\uDB40\\uDD6A'],
  [String.fromCodePoint(0xE016B), '\\uDB40\\uDD6B'],
  [String.fromCodePoint(0xE016C), '\\uDB40\\uDD6C'],
  [String.fromCodePoint(0xE016D), '\\uDB40\\uDD6D'],
  [String.fromCodePoint(0xE016E), '\\uDB40\\uDD6E'],
  [String.fromCodePoint(0xE016F), '\\uDB40\\uDD6F'],
  [String.fromCodePoint(0xE0170), '\\uDB40\\uDD70'],
  [String.fromCodePoint(0xE0171), '\\uDB40\\uDD71'],
  [String.fromCodePoint(0xE0172), '\\uDB40\\uDD72'],
  [String.fromCodePoint(0xE0173), '\\uDB40\\uDD73'],
  [String.fromCodePoint(0xE0174), '\\uDB40\\uDD74'],
  [String.fromCodePoint(0xE0175), '\\uDB40\\uDD75'],
  [String.fromCodePoint(0xE0176), '\\uDB40\\uDD76'],
  [String.fromCodePoint(0xE0177), '\\uDB40\\uDD77'],
  [String.fromCodePoint(0xE0178), '\\uDB40\\uDD78'],
  [String.fromCodePoint(0xE0179), '\\uDB40\\uDD79'],
  [String.fromCodePoint(0xE017A), '\\uDB40\\uDD7A'],
  [String.fromCodePoint(0xE017B), '\\uDB40\\uDD7B'],
  [String.fromCodePoint(0xE017C), '\\uDB40\\uDD7C'],
  [String.fromCodePoint(0xE017D), '\\uDB40\\uDD7D'],
  [String.fromCodePoint(0xE017E), '\\uDB40\\uDD7E'],
  [String.fromCodePoint(0xE017F), '\\uDB40\\uDD7F'],
  [String.fromCodePoint(0xE0180), '\\uDB40\\uDD80'],
  [String.fromCodePoint(0xE0181), '\\uDB40\\uDD81'],
  [String.fromCodePoint(0xE0182), '\\uDB40\\uDD82'],
  [String.fromCodePoint(0xE0183), '\\uDB40\\uDD83'],
  [String.fromCodePoint(0xE0184), '\\uDB40\\uDD84'],
  [String.fromCodePoint(0xE0185), '\\uDB40\\uDD85'],
  [String.fromCodePoint(0xE0186), '\\uDB40\\uDD86'],
  [String.fromCodePoint(0xE0187), '\\uDB40\\uDD87'],
  [String.fromCodePoint(0xE0188), '\\uDB40\\uDD88'],
  [String.fromCodePoint(0xE0189), '\\uDB40\\uDD89'],
  [String.fromCodePoint(0xE018A), '\\uDB40\\uDD8A'],
  [String.fromCodePoint(0xE018B), '\\uDB40\\uDD8B'],
  [String.fromCodePoint(0xE018C), '\\uDB40\\uDD8C'],
  [String.fromCodePoint(0xE018D), '\\uDB40\\uDD8D'],
  [String.fromCodePoint(0xE018E), '\\uDB40\\uDD8E'],
  [String.fromCodePoint(0xE018F), '\\uDB40\\uDD8F'],
  [String.fromCodePoint(0xE0190), '\\uDB40\\uDD90'],
  [String.fromCodePoint(0xE0191), '\\uDB40\\uDD91'],
  [String.fromCodePoint(0xE0192), '\\uDB40\\uDD92'],
  [String.fromCodePoint(0xE0193), '\\uDB40\\uDD93'],
  [String.fromCodePoint(0xE0194), '\\uDB40\\uDD94'],
  [String.fromCodePoint(0xE0195), '\\uDB40\\uDD95'],
  [String.fromCodePoint(0xE0196), '\\uDB40\\uDD96'],
  [String.fromCodePoint(0xE0197), '\\uDB40\\uDD97'],
  [String.fromCodePoint(0xE0198), '\\uDB40\\uDD98'],
  [String.fromCodePoint(0xE0199), '\\uDB40\\uDD99'],
  [String.fromCodePoint(0xE019A), '\\uDB40\\uDD9A'],
  [String.fromCodePoint(0xE019B), '\\uDB40\\uDD9B'],
  [String.fromCodePoint(0xE019C), '\\uDB40\\uDD9C'],
  [String.fromCodePoint(0xE019D), '\\uDB40\\uDD9D'],
  [String.fromCodePoint(0xE019E), '\\uDB40\\uDD9E'],
  [String.fromCodePoint(0xE019F), '\\uDB40\\uDD9F'],
  [String.fromCodePoint(0xE01A0), '\\uDB40\\uDDA0'],
  [String.fromCodePoint(0xE01A1), '\\uDB40\\uDDA1'],
  [String.fromCodePoint(0xE01A2), '\\uDB40\\uDDA2'],
  [String.fromCodePoint(0xE01A3), '\\uDB40\\uDDA3'],
  [String.fromCodePoint(0xE01A4), '\\uDB40\\uDDA4'],
  [String.fromCodePoint(0xE01A5), '\\uDB40\\uDDA5'],
  [String.fromCodePoint(0xE01A6), '\\uDB40\\uDDA6'],
  [String.fromCodePoint(0xE01A7), '\\uDB40\\uDDA7'],
  [String.fromCodePoint(0xE01A8), '\\uDB40\\uDDA8'],
  [String.fromCodePoint(0xE01A9), '\\uDB40\\uDDA9'],
  [String.fromCodePoint(0xE01AA), '\\uDB40\\uDDAA'],
  [String.fromCodePoint(0xE01AB), '\\uDB40\\uDDAB'],
  [String.fromCodePoint(0xE01AC), '\\uDB40\\uDDAC'],
  [String.fromCodePoint(0xE01AD), '\\uDB40\\uDDAD'],
  [String.fromCodePoint(0xE01AE), '\\uDB40\\uDDAE'],
  [String.fromCodePoint(0xE01AF), '\\uDB40\\uDDAF'],
  [String.fromCodePoint(0xE01B0), '\\uDB40\\uDDB0'],
  [String.fromCodePoint(0xE01B1), '\\uDB40\\uDDB1'],
  [String.fromCodePoint(0xE01B2), '\\uDB40\\uDDB2'],
  [String.fromCodePoint(0xE01B3), '\\uDB40\\uDDB3'],
  [String.fromCodePoint(0xE01B4), '\\uDB40\\uDDB4'],
  [String.fromCodePoint(0xE01B5), '\\uDB40\\uDDB5'],
  [String.fromCodePoint(0xE01B6), '\\uDB40\\uDDB6'],
  [String.fromCodePoint(0xE01B7), '\\uDB40\\uDDB7'],
  [String.fromCodePoint(0xE01B8), '\\uDB40\\uDDB8'],
  [String.fromCodePoint(0xE01B9), '\\uDB40\\uDDB9'],
  [String.fromCodePoint(0xE01BA), '\\uDB40\\uDDBA'],
  [String.fromCodePoint(0xE01BB), '\\uDB40\\uDDBB'],
  [String.fromCodePoint(0xE01BC), '\\uDB40\\uDDBC'],
  [String.fromCodePoint(0xE01BD), '\\uDB40\\uDDBD'],
  [String.fromCodePoint(0xE01BE), '\\uDB40\\uDDBE'],
  [String.fromCodePoint(0xE01BF), '\\uDB40\\uDDBF'],
  [String.fromCodePoint(0xE01C0), '\\uDB40\\uDDC0'],
  [String.fromCodePoint(0xE01C1), '\\uDB40\\uDDC1'],
  [String.fromCodePoint(0xE01C2), '\\uDB40\\uDDC2'],
  [String.fromCodePoint(0xE01C3), '\\uDB40\\uDDC3'],
  [String.fromCodePoint(0xE01C4), '\\uDB40\\uDDC4'],
  [String.fromCodePoint(0xE01C5), '\\uDB40\\uDDC5'],
  [String.fromCodePoint(0xE01C6), '\\uDB40\\uDDC6'],
  [String.fromCodePoint(0xE01C7), '\\uDB40\\uDDC7'],
  [String.fromCodePoint(0xE01C8), '\\uDB40\\uDDC8'],
  [String.fromCodePoint(0xE01C9), '\\uDB40\\uDDC9'],
  [String.fromCodePoint(0xE01CA), '\\uDB40\\uDDCA'],
  [String.fromCodePoint(0xE01CB), '\\uDB40\\uDDCB'],
  [String.fromCodePoint(0xE01CC), '\\uDB40\\uDDCC'],
  [String.fromCodePoint(0xE01CD), '\\uDB40\\uDDCD'],
  [String.fromCodePoint(0xE01CE), '\\uDB40\\uDDCE'],
  [String.fromCodePoint(0xE01CF), '\\uDB40\\uDDCF'],
  [String.fromCodePoint(0xE01D0), '\\uDB40\\uDDD0'],
  [String.fromCodePoint(0xE01D1), '\\uDB40\\uDDD1'],
  [String.fromCodePoint(0xE01D2), '\\uDB40\\uDDD2'],
  [String.fromCodePoint(0xE01D3), '\\uDB40\\uDDD3'],
  [String.fromCodePoint(0xE01D4), '\\uDB40\\uDDD4'],
  [String.fromCodePoint(0xE01D5), '\\uDB40\\uDDD5'],
  [String.fromCodePoint(0xE01D6), '\\uDB40\\uDDD6'],
  [String.fromCodePoint(0xE01D7), '\\uDB40\\uDDD7'],
  [String.fromCodePoint(0xE01D8), '\\uDB40\\uDDD8'],
  [String.fromCodePoint(0xE01D9), '\\uDB40\\uDDD9'],
  [String.fromCodePoint(0xE01DA), '\\uDB40\\uDDDA'],
  [String.fromCodePoint(0xE01DB), '\\uDB40\\uDDDB'],
  [String.fromCodePoint(0xE01DC), '\\uDB40\\uDDDC'],
  [String.fromCodePoint(0xE01DD), '\\uDB40\\uDDDD'],
  [String.fromCodePoint(0xE01DE), '\\uDB40\\uDDDE'],
  [String.fromCodePoint(0xE01DF), '\\uDB40\\uDDDF'],
  [String.fromCodePoint(0xE01E0), '\\uDB40\\uDDE0'],
  [String.fromCodePoint(0xE01E1), '\\uDB40\\uDDE1'],
  [String.fromCodePoint(0xE01E2), '\\uDB40\\uDDE2'],
  [String.fromCodePoint(0xE01E3), '\\uDB40\\uDDE3'],
  [String.fromCodePoint(0xE01E4), '\\uDB40\\uDDE4'],
  [String.fromCodePoint(0xE01E5), '\\uDB40\\uDDE5'],
  [String.fromCodePoint(0xE01E6), '\\uDB40\\uDDE6'],
  [String.fromCodePoint(0xE01E7), '\\uDB40\\uDDE7'],
  [String.fromCodePoint(0xE01E8), '\\uDB40\\uDDE8'],
  [String.fromCodePoint(0xE01E9), '\\uDB40\\uDDE9'],
  [String.fromCodePoint(0xE01EA), '\\uDB40\\uDDEA'],
  [String.fromCodePoint(0xE01EB), '\\uDB40\\uDDEB'],
  [String.fromCodePoint(0xE01EC), '\\uDB40\\uDDEC'],
  [String.fromCodePoint(0xE01ED), '\\uDB40\\uDDED'],
  [String.fromCodePoint(0xE01EE), '\\uDB40\\uDDEE'],
  [String.fromCodePoint(0xE01EF), '\\uDB40\\uDDEF'],
]);

// Regex pattern for bidi/control characters (for testing presence)
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
function escapeBidi(text) {
  if (typeof text !== 'string') {
    return String(text);
  }
  let result = text;
  for (const [char, escape] of BIDI_ESCAPE_MAP) {
    result = result.split(char).join(escape);
  }
  return result;
}

/**
 * Escape markdown-special characters that could break formatting or
 * enable injection attacks. This handles standard markdown metacharacters
 * that are dangerous in inline text context.
 *
 * For general inline text, escapes: ampersand (first, to block entity injection),
 * angle brackets (HTML/script), backslash, backtick, asterisk, underscore,
 * curly braces, square brackets, parentheses, hash.
 * For table cells, escapes: ampersand, angle brackets, pipe, backtick,
 * square brackets, parentheses, exclamation mark (to block links/images).
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
function escapeMarkdown(text, options = {}) {
  const { forTableCell = false } = options;
  if (typeof text !== 'string') {
    return String(text);
  }
  // Escape ampersand FIRST to prevent numeric entity injection (&#x202E; etc.)
  let result = text.replace(/&/g, '&amp;');
  // Escape angle brackets to prevent HTML/script injection
  result = result.replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // Escape backslashes to avoid double-escaping
  result = result.replace(/\\/g, '\\\\');
  
  if (forTableCell) {
    // For table cells, escape pipe (breaks columns), backtick (code),
    // and link/image syntax chars that could forge links in cells
    result = result.replace(/([`|\[\]()!])/g, '\\$1');
  } else {
    // For inline text, escape chars that could break formatting
    // Backtick (code), asterisk/underscore (emphasis), brackets (links),
    // parens (links/images), braces (mustache), hash (headings)
    result = result.replace(/([`*_{}\[\]()#])/g, '\\$1');
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
 * // returns '\\\\u200F \\*world\\*'
 */
function escapeForMarkdown(text, options) {
  const bidiEscaped = escapeBidi(text);
  return escapeMarkdown(bidiEscaped, options);
}

/**
 * Check if a string contains any bidi/control characters.
 *
 * @param {string} text - The input text to check.
 * @returns {boolean} True if bidi/control characters are present.
 */
function containsBidiChars(text) {
  if (typeof text !== 'string') {
    return false;
  }
  return BIDI_CHAR_TEST_PATTERN.test(text);
}

// Iterative stable serialization: sorted object keys, original array order, JSON scalars.
function stable(value) {
  const output=[], stack=[{value}];
  while(stack.length){
    const item=stack.pop();
    if(Object.hasOwn(item,'text')){output.push(item.text);continue;}
    const v=item.value;
    if(v===null || typeof v!=='object'){const s=JSON.stringify(v);if(s===undefined)throw Error('unsupported packet value');output.push(s);continue;}
    const array=Array.isArray(v),keys=array ? v.map((_,i)=>i) : Object.keys(v).sort();
    output.push(array?'[':'{');stack.push({text:array?']':'}'});
    for(let i=keys.length-1;i>=0;i--){const k=keys[i];stack.push({value:v[k]});if(!array)stack.push({text:JSON.stringify(k)+':'});if(i>0)stack.push({text:','});}
  }
  return output.join('');
}

async function sha256(bytes) {
  if(!globalThis.crypto?.subtle)throw Error('local cryptography unavailable; export disabled');
  return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
}

function ref(slot,e){return {slot,run_id:e.run_id,seq:e.seq,turn:e.turn,type:e.type};}

function tag(configs,field){
  if(configs.length>1)return {state:'conflicting'};
  if(configs.length!==1 || !Object.hasOwn(configs[0].payload,field))return {state:'missing'};
  return {state:'present',value:configs[0].payload[field]};
}

function source(data){
  if(!data || !/^[0-9a-f]{64}$/.test(data.sha256||'') || !Number.isSafeInteger(data.byteLength))throw Error('both source byte hashes are required');
  return {sha256:data.sha256,byte_length:data.byteLength,run_id:data.episode.runId,turn_range:[data.episode.turns[0],data.episode.turns.at(-1)],event_count:data.episode.events.length,run_end_present:data.episode.events.some(e=>e.type==='run.end')};
}

function build(sources,selection){
  const selected=[...new Set(selection)].sort((a,b)=>a-b),union=CompareEvidence.turns(sources.left?.episode,sources.right?.episode);
  if(!selected.length || selected.length>32 || selected.some(t=>!Number.isSafeInteger(t)||!union.includes(t)))throw Error('select 1–32 recorded turns');
  const leftConfigs=CompareEvidence.config(sources.left?.episode),rightConfigs=CompareEvidence.config(sources.right?.episode);
  const packet={schema_version:SCHEMA,exporter_version:VERSION,scope:'selected-turn-record-comparison',sources:{left:source(sources.left),right:source(sources.right)},selection:{turns:selected,alignment:'last-record-at-or-before-turn'},configuration:{context:'file-level',fields:CompareEvidence.configuration(sources.left.episode,sources.right.episode).map(row=>({field:row.field,status:row.status,left:tag(leftConfigs,row.field),right:tag(rightConfigs,row.field)})),records:{left:leftConfigs.map(e=>ref('left',e)),right:rightConfigs.map(e=>ref('right',e))}},turns:[],observations:[],disturbances:[],limitations:[...CAVEATS]};
  for(const slot of ['left','right'])if(!packet.sources[slot].run_end_present)packet.limitations.push(`${slot}: no run.end recorded.`);
  if(stable(packet.sources.left.turn_range)!==stable(packet.sources.right.turn_range))packet.limitations.push('source turn ranges differ; horizons are unequal.');
  for(const row of packet.configuration.fields)if(row.status.includes('unknown')||row.status.includes('conflicting'))packet.limitations.push(`${row.field}: ${row.status}.`);
  for(const turn of selected){
    const states={left:CompareEvidence.atTurn(sources.left.episode,turn),right:CompareEvidence.atTurn(sources.right.episode,turn)};
    const entry={turn,left:null,right:null,delta:{}};
    for(const slot of ['left','right']){
      const state=states[slot];entry[slot]={status:state.status,counts:{},contributors:{}};
      if(!state.available)packet.limitations.push(`${slot}, turn ${turn}: ${state.status}.`);
      for(const metric of CompareEvidence.METRICS){entry[slot].counts[metric]=state.counts?.[metric].length??null;entry[slot].contributors[metric]=state.counts ? state.counts[metric].map(e=>ref(slot,e)) : null;}
      packet.observations.push({selected_turn:turn,slot,records:[...(state.state?.observations.values()||[])].map(e=>({...ref(slot,e),agent_id:e.agent_id,carried_forward:e.turn<turn}))});
      packet.disturbances.push({selected_turn:turn,slot,records:(state.state?.disturbances||[]).map(e=>ref(slot,e))});
    }
    for(const metric of CompareEvidence.METRICS)entry.delta[metric]=states.left.available&&states.right.available ? entry.right.counts[metric]-entry.left.counts[metric] : null;
    packet.turns.push(entry);
  }
  // Snapshot configuration values and freeze iteratively; never freeze caller-owned logs.
  return JSON.parse(stable(packet));
}

/**
 * Escape text for safe markdown export.
 * - Escapes C0/C1 controls (except \t, \n, \r which get special handling)
 * - Escapes U+2028/2029 (line/paragraph separators)
 * - Escapes all bidi formatting chars (LRM/RLM/ALM, LRE/RLE/LRO/RLO, LRI/RLI/FSI/PDI)
 * - Escapes optional format chars (ZWSP/ZWNJ/ZWJ/SHY/BOM)
 * - Escapes & FIRST to prevent numeric entity injection (e.g., &#x202E;)
 * - Escapes < and > with numeric entities to prevent HTML/script injection
 * - Escapes \n and \r to prevent markdown breakout via forged headings/links
 * - Escapes punctuation with numeric entities (original master behavior)
 *
 * @param {string} value - The value to escape.
 * @returns {string} The escaped text safe for markdown.
 */
function text(value) {
  let str = String(value);
  // First escape & to prevent numeric entity injection like &#x202E;
  str = str.replace(/&/g, '&amp;');
  // Escape < and > to prevent HTML/script injection
  str = str.replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // Escape punctuation with numeric entities (original master behavior for safety)
  // Pattern [!-/:-@\[-`{-~] covers backslash (0x5C) and all punctuation
  str = str.replace(/[!-/:-@\[-`{-~]/g, c => '&#' + c.charCodeAt(0) + ';');
  // Escape bidi/control characters using the map
  str = escapeBidi(str);
  // Escape newlines and carriage returns to prevent markdown breakout
  // Done after punctuation so the literal \\n sequence isn't re-escaped
  str = str.replace(/\n/g, '\\n').replace(/\r/g, '\\r');
  return str;
}

function markdown(packet){
  const lines=['# selected-turn evidence packet','',`packet id: ${packet.packet_id}`,`schema: ${packet.schema_version}`,`exporter: ${packet.exporter_version}`,'',`selected turns: ${packet.selection.turns.join(', ')}`,`alignment: ${packet.selection.alignment}`,'','## sources'];
  for(const slot of ['left','right']){const s=packet.sources[slot];lines.push('',`### ${slot}`,`sha256: ${s.sha256}`,`bytes: ${s.byte_length}; records: ${s.event_count}; turns: ${text(s.turn_range.join('–'))}; run.end present: ${s.run_end_present}`,`run id: ${text(s.run_id)}`);}
  lines.push('','## logged configuration / file-level context');
  for(const row of packet.configuration.fields)lines.push('',`- ${text(row.field)}: ${text(row.status)}`,`  - left: ${text(stable(row.left))}`,`  - right: ${text(stable(row.right))}`);
  for(const slot of ['left','right'])lines.push(`- ${slot} configuration references: ${text(stable(packet.configuration.records[slot]))}`);
  for(const turn of packet.turns){
    lines.push('',`## turn ${turn.turn}`,`left: ${turn.left.status}; right: ${turn.right.status}`,'','| event count | left | right | right − left |','|---|---:|---:|---:|');
    for(const metric of CompareEvidence.METRICS)lines.push(`| ${metric} | ${turn.left.counts[metric]??'unavailable'} | ${turn.right.counts[metric]??'unavailable'} | ${turn.delta[metric]??'unavailable'} |`);
    lines.push('','supporting references:');
    for(const slot of ['left','right'])for(const metric of CompareEvidence.METRICS)lines.push(`- ${slot} ${metric}: ${turn[slot].contributors[metric]===null ? 'unavailable' : text(stable(turn[slot].contributors[metric]))}`);
    for(const kind of ['observations','disturbances'])for(const item of packet[kind].filter(x=>x.selected_turn===turn.turn))lines.push(`- ${item.slot} ${kind}: ${text(stable(item.records))}`);
  }
  lines.push('','## limitations',...packet.limitations.map(s=>'- '+text(s)),'');return lines.join('\n');
}

async function prepare(sources,selection){
  const packet=build(sources,selection),encoded=new TextEncoder();
  const base=stable(packet);
  if(encoded.encode(base).length>MAX_BYTES)throw Error('select fewer turns: evidence exceeds 2 mib');
  packet.packet_id=await sha256(encoded.encode(base));
  const json=stable(packet)+'\n',md=markdown(packet);
  const sizes={json:encoded.encode(json).length,markdown:encoded.encode(md).length};
  if(sizes.json>MAX_BYTES||sizes.markdown>MAX_BYTES)throw Error('select fewer turns: evidence exceeds 2 mib');
  const stack=[packet];while(stack.length){const o=stack.pop();Object.freeze(o);for(const v of Object.values(o))if(v&&typeof v==='object')stack.push(v);}
  return Object.freeze({packet,json,markdown:md,sizes:Object.freeze(sizes)});
}

// Export both the legacy API and new helper functions
const Evidence = {
  SCHEMA, VERSION, MAX_BYTES, CAVEATS,
  stable, sha256, build, markdown, prepare, text,
  // New helper exports for testing and direct use
  escapeBidi, escapeMarkdown, escapeForMarkdown, containsBidiChars,
  // Export BIDI_ESCAPE_MAP for inspection/testing
  BIDI_ESCAPE_MAP,
};

if (typeof module !== 'undefined') {
  module.exports = Evidence;
} else {
  globalThis.Evidence = Evidence;
}

// ESM named export shim for node --test compatibility
// This allows the ESM test file to import named exports from this CJS module
// Scoped to avoid polluting globalThis in production
if (typeof process !== 'undefined' && process.argv?.[1]?.includes?.('evidence.test.js')) {
  if (typeof globalThis.ESM_EXPORTS === 'undefined') {
    globalThis.ESM_EXPORTS = {};
  }
  globalThis.ESM_EXPORTS['./evidence.js'] = Evidence;
}
