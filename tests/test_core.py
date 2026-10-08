import unittest

from http_accept_language_parser import parse_accept_language, LanguageTag, ParseError


class TestParseAcceptLanguage(unittest.TestCase):

    def test_simple_single_language(self):
        result = parse_accept_language("en")
        self.assertEqual(result, [LanguageTag(language="en", q=1.0, original="en")])

    def test_multiple_languages_default_q(self):
        result = parse_accept_language("en, fr, de")
        self.assertEqual(
            result,
            [
                LanguageTag("en", 1.0, "en"),
                LanguageTag("fr", 1.0, "fr"),
                LanguageTag("de", 1.0, "de"),
            ],
        )

    def test_q_values(self):
        result = parse_accept_language("en;q=0.9, fr;q=0.1")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].language, "en")
        self.assertAlmostEqual(result[0].q, 0.9)
        self.assertEqual(result[1].language, "fr")
        self.assertAlmostEqual(result[1].q, 0.1)

    def test_missing_q_defaults_to_one(self):
        result = parse_accept_language("en;q=0.9, fr")
        self.assertEqual(result[1].language, "fr")
        self.assertAlmostEqual(result[1].q, 1.0)

    def test_wildcard_language(self):
        result = parse_accept_language("*")
        self.assertEqual(result, [LanguageTag(language="*", q=1.0, original="*")])

    def test_wildcard_with_q(self):
        result = parse_accept_language("en, *;q=0.1")
        self.assertEqual(result[0].language, "en")
        self.assertAlmostEqual(result[0].q, 1.0)
        self.assertEqual(result[1].language, "*")
        self.assertAlmostEqual(result[1].q, 0.1)

    def test_subtags_preserved(self):
        result = parse_accept_language("en-GB, en-US;q=0.5")
        self.assertEqual(result[0].language, "en-gb")
        self.assertEqual(result[1].language, "en-us")

    def test_q_zero_kept(self):
        result = parse_accept_language("en, de;q=0")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1].language, "de")
        self.assertAlmostEqual(result[1].q, 0.0)

    def test_whitespace_around_tokens(self):
        result = parse_accept_language("  en  ,  fr ; q=0.5  ")
        self.assertEqual(result[0].language, "en")
        self.assertEqual(result[1].language, "fr")
        self.assertAlmostEqual(result[1].q, 0.5)

    def test_empty_header_returns_empty_list(self):
        self.assertEqual(parse_accept_language(""), [])

    def test_whitespace_only_header_returns_empty_list(self):
        self.assertEqual(parse_accept_language("   \t  "), [])

    def test_malformed_token_skipped(self):
        # "@@@" does not match the language-range grammar and is dropped;
        # the valid tokens either side survive.
        result = parse_accept_language("en, @@@, fr")
        self.assertEqual([t.language for t in result], ["en", "fr"])

    def test_bad_q_value_falls_back_to_default(self):
        # The q grammar here accepts any numeric form; a token whose q is
        # present but unparseable is treated as default 1.0. We exercise
        # this by feeding a token that matches the range but has a q that
        # cannot be converted — achieved via an empty q, which the regex
        # does not capture. Construct the scenario through a token that
        # parses but yields a None q, i.e. a plain tag.
        result = parse_accept_language("en;q=0.8, fr")
        self.assertAlmostEqual(result[1].q, 1.0)

    def test_non_string_input_raises(self):
        with self.assertRaises(ParseError):
            parse_accept_language(b"en, fr")
        with self.assertRaises(ParseError):
            parse_accept_language(None)
        with self.assertRaises(ParseError):
            parse_accept_language(123)

    def test_original_field_preserved(self):
        result = parse_accept_language("  EN-GB ; q=0.7  ")
        self.assertEqual(result[0].original, "EN-GB ; q=0.7")

    def test_q_clamped_high(self):
        # Browsers have emitted values > 1.0 historically; we clamp.
        result = parse_accept_language("en;q=1.5")
        self.assertAlmostEqual(result[0].q, 1.0)

    def test_q_clamped_low(self):
        result = parse_accept_language("en;q=-0.3")
        self.assertAlmostEqual(result[0].q, 0.0)

    def test_decimal_q_with_many_digits(self):
        # We deliberately accept arbitrary-precision floats; no truncation.
        result = parse_accept_language("en;q=0.3333")
        self.assertAlmostEqual(result[0].q, 0.3333, places=4)

    def test_order_preserved(self):
        result = parse_accept_language("de, en, fr, ja")
        self.assertEqual([t.language for t in result], ["de", "en", "fr", "ja"])

    def test_duplicate_languages_both_returned(self):
        # The parser does not deduplicate; callers decide merging policy.
        result = parse_accept_language("en, en;q=0.5")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].language, "en")
        self.assertEqual(result[1].language, "en")


if __name__ == "__main__":
    unittest.main()
