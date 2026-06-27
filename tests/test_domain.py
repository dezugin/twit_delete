import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from twit_cleaner.app import build_runtime
from twit_cleaner.cli import parse_args
from twit_cleaner.keywords import classify_post, load_custom_terms, load_keyword_rules
from twit_cleaner.models import Target
from twit_cleaner.posts import combined_action_target, exclusions_apply
from twit_cleaner.urls import canonical_owned_status_url


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KEYWORD_PROFILES = PROJECT_ROOT / "twit_cleaner" / "keyword_profiles.json"


class DomainTests(unittest.TestCase):
    def test_owned_status_url_requires_profile_handle(self) -> None:
        profile = "https://x.com/example/with_replies"
        self.assertEqual(
            canonical_owned_status_url("/example/status/123?s=20", profile),
            "https://x.com/example/status/123",
        )
        self.assertIsNone(canonical_owned_status_url("/someone/status/123", profile))

    def test_active_unretweet_has_priority(self) -> None:
        self.assertEqual(combined_action_target(True, None), Target.RETWEETS)
        self.assertEqual(
            combined_action_target(True, "https://x.com/example/status/123"),
            Target.RETWEETS,
        )
        self.assertEqual(
            combined_action_target(False, "https://x.com/example/status/123"),
            Target.POSTS,
        )

    def test_exclusions_never_block_unretweet(self) -> None:
        self.assertTrue(exclusions_apply(Target.POSTS, "custom"))
        self.assertFalse(exclusions_apply(Target.RETWEETS, "custom"))

    def test_profiles_work_for_matching_and_exclusion(self) -> None:
        rules = load_keyword_rules(KEYWORD_PROFILES, "personal", "politics")
        self.assertIn("family", rules.match_keywords)
        self.assertIn("politics", rules.exclusion_hashtags)
        self.assertTrue(
            classify_post(
                "Family vacation #personal",
                set(rules.match_keywords),
                set(rules.match_hashtags),
            ).matched
        )

        reverse_rules = load_keyword_rules(KEYWORD_PROFILES, "politics", "work")
        self.assertIn("trump", reverse_rules.match_keywords)
        self.assertIn("portfolio", reverse_rules.exclusion_keywords)

    def test_custom_files_accept_space_and_newline_separated_terms(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "custom.txt"
            path.write_text(
                "// This line is ignored\nfamily portfolio\n#keepme birthday\n",
                encoding="utf-8",
            )
            keywords, hashtags = load_custom_terms(path)
        self.assertEqual(keywords, frozenset({"family", "portfolio", "birthday"}))
        self.assertEqual(hashtags, frozenset({"keepme"}))

    def test_custom_modes_require_their_files(self) -> None:
        with self.assertRaisesRegex(ValueError, "--match custom requires"):
            parse_args(["--profile-url", "https://x.com/example", "--match", "custom"])
        with self.assertRaisesRegex(ValueError, "--exclude-mode custom requires"):
            parse_args(["--profile-url", "https://x.com/example", "--exclude-mode", "custom"])

    def test_custom_files_are_wired_into_runtime(self) -> None:
        with TemporaryDirectory() as directory:
            match_path = Path(directory) / "match.txt"
            exclude_path = Path(directory) / "exclude.txt"
            match_path.write_text("gaming #games", encoding="utf-8")
            exclude_path.write_text("family #keepme", encoding="utf-8")
            args = parse_args(
                [
                    "--profile-url",
                    "https://x.com/example",
                    "--match",
                    "custom",
                    "--match-keywords-file",
                    str(match_path),
                    "--exclude-mode",
                    "custom",
                    "--exclude-keywords-file",
                    str(exclude_path),
                ]
            )
            _, options, keywords, hashtags, _ = build_runtime(args)
        self.assertEqual(keywords, {"gaming"})
        self.assertEqual(hashtags, {"games"})
        self.assertEqual(options.exclusion_keywords, frozenset({"family"}))
        self.assertEqual(options.exclusion_hashtags, frozenset({"keepme"}))

    def test_inline_keywords_support_phrases_and_hashtags(self) -> None:
        args = parse_args(
            [
                "--profile-url",
                "https://x.com/example",
                "--match",
                "custom",
                "--match-keywords",
                "prime minister",
                "#election",
                "--exclude-keywords",
                "family photo",
                "#keepme",
            ]
        )
        _, options, keywords, hashtags, _ = build_runtime(args)
        self.assertEqual(keywords, {"prime minister"})
        self.assertEqual(hashtags, {"election"})
        self.assertEqual(args.exclude_mode, "custom")
        self.assertEqual(options.exclusion_keywords, frozenset({"family photo"}))
        self.assertEqual(options.exclusion_hashtags, frozenset({"keepme"}))

    def test_inline_keywords_augment_a_built_in_profile(self) -> None:
        args = parse_args(
            [
                "--profile-url",
                "https://x.com/example",
                "--match",
                "work",
                "--match-keywords",
                "freelance",
            ]
        )
        _, _, keywords, _, _ = build_runtime(args)
        self.assertIn("work", keywords)
        self.assertIn("freelance", keywords)

    def test_all_built_in_profiles_are_valid_on_both_sides(self) -> None:
        for profile in ("politics", "personal", "work"):
            args = parse_args(
                [
                    "--profile-url",
                    "https://x.com/example",
                    "--match",
                    profile,
                    "--exclude-mode",
                    profile,
                ]
            )
            self.assertEqual(args.match, profile)
            self.assertEqual(args.exclude_mode, profile)

    def test_delete_all_shortcut_is_destructive_all_mode(self) -> None:
        args = parse_args(["--profile-url", "https://x.com/example", "--delete-all"])
        self.assertTrue(args.delete)
        self.assertEqual(args.match, "all")


if __name__ == "__main__":
    unittest.main()
