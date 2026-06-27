import unittest
from pathlib import Path

from twit_cleaner.cli import parse_args
from twit_cleaner.keywords import classify_post, load_keyword_rules
from twit_cleaner.models import Target
from twit_cleaner.posts import combined_action_target, exclusions_apply
from twit_cleaner.urls import canonical_owned_status_url


PROJECT_ROOT = Path(__file__).resolve().parent.parent


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

    def test_keyword_profiles_and_custom_defaults(self) -> None:
        rules = load_keyword_rules(PROJECT_ROOT / "keyword_profiles.json", "custom")
        self.assertEqual(len(rules.political_keywords), 44)
        self.assertEqual(len(rules.political_hashtags), 14)
        self.assertFalse(rules.exclusion_keywords)
        self.assertFalse(rules.exclusion_hashtags)
        self.assertTrue(
            classify_post(
                "Trump #politics",
                set(rules.political_keywords),
                set(rules.political_hashtags),
            ).matched
        )

    def test_delete_all_shortcut_is_destructive_all_mode(self) -> None:
        args = parse_args(["--profile-url", "https://x.com/example", "--delete-all"])
        self.assertTrue(args.delete)
        self.assertEqual(args.match, "all")


if __name__ == "__main__":
    unittest.main()
