# Twit Cleaner

A Playwright browser-navigation tool for cleaning your X account around the parts of life you care about. Remove personal history, clean up work-related posts, filter political content, preserve one profile while deleting another, and undo your reposts. Scans are unlimited unless `--max-posts` is supplied.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install twit-cleaner
python -m playwright install chromium firefox
twit-cleaner --help
python -m twit_cleaner --help
```

## Existing Chrome Login

Start Chrome with remote debugging, log in to X, and leave the window open:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-x-cdp" --ozone-platform=x11
```

For Chromium:

```bash
chromium --remote-debugging-port=9222 --user-data-dir="$HOME/.chromium-x-cdp" --ozone-platform=x11
```

Confirm that the connection works:

```bash
curl http://127.0.0.1:9222/json/version
```

## Warning: Delete Everything

**Unsafe and irreversible:** this command makes one interleaved pass through `/with_replies`. For each card, it undoes an active repost or deletes the card when its primary permalink belongs to your profile. It does not inspect profile keywords and does not ask for confirmation in the terminal. X still displays its normal per-item confirmation dialog, which the tool accepts automatically.

With your remote-debugging Chrome window open and logged in, run:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all
```

Reposts, replies, and original posts are handled in the order they appear. Each item is processed sequentially: find one, choose Undo repost or Delete, act on it, query the updated `/with_replies` timeline, then find the next one. If one of your own posts is also reposted, the tool undoes the repost first, then sees the same owned permalink again and deletes the post. Press `Ctrl+C` to stop.

Before every removal, the tool checks for an active `unretweet` control. That control means your logged-in account reposted the item; the original post may belong to any account. Those items use **Undo repost** without requiring the original author's permalink to match your handle. Only post and reply deletion requires a permalink matching `/YOUR_HANDLE/status/...`, which prevents conversation cards from other accounts from being deleted. The tool first tries the timeline menu; if that fails, it opens the owned permalink in a temporary tab and retries there.

Some stale timeline cards say that you reposted them while X only offers **Repost** instead of **Undo repost**. When such a card is selected for removal, Twit Cleaner repairs the state by reposting it and immediately undoing that repost. This briefly creates a new repost action. Run without `--delete` first to preview these cards as `would repost, then undo repost`.

## Choose What To Clean

Every built-in profile works with both `--match` and `--exclude-mode`.

| Profile    | Typical content                                                  | Match example                        | Exclusion example                              |
| ---------- | ---------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------- |
| `personal` | Family, friends, memories, birthdays, vacations, hobbies         | Delete old personal posts            | Preserve personal posts during another cleanup |
| `work`     | Projects, clients, jobs, hiring, portfolios, conferences         | Delete an old professional footprint | Preserve career history                        |
| `politics` | Elections, politicians, parties, governments, political hashtags | Delete political posts or replies    | Preserve political commentary                  |
| `custom`   | Your command-line terms or custom files                          | Match your own topic                 | Preserve your own topic                        |

`--match PROFILE` selects content for deletion. `--exclude-mode PROFILE` protects matching owned posts and replies. Repost removal is never blocked by an exclusion profile.

Dry-run personal posts without deleting anything:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match personal
```

Delete personal replies while preserving work-related replies:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target replies --match personal --exclude-mode work --delete
```

Dry-run work-related posts:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match work
```

Delete work-related posts while preserving personal posts:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match work --exclude-mode personal --delete
```

Delete political posts while preserving personal posts:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match politics --exclude-mode personal --delete
```

Preserve your professional footprint while removing everything else:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all --exclude-mode work
```

The built-in terms live in [`twit_cleaner/keyword_profiles.json`](twit_cleaner/keyword_profiles.json). Personal includes family, friends, memories, birthdays, vacations, and hobbies. Work includes projects, clients, careers, jobs, hiring, portfolios, and conferences. Edit that JSON or use `--keyword-profiles PATH` to replace all three built-in profiles.

## Custom Keyword Files

Custom terms are stored outside the JSON. Use one file for matching and another for exclusion. Terms may be separated by spaces or newlines, are case-insensitive, and become hashtags when prefixed with `#`. Lines beginning with `//` are comments.

Edit [`custom_match_keywords.txt`](custom_match_keywords.txt):

```text
football gaming photography
#sports #games
```

Edit [`custom_exclusion_keywords.txt`](custom_exclusion_keywords.txt):

```text
family portfolio birthday
#keepme #work
```

Use both custom files:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match custom --match-keywords-file ./custom_match_keywords.txt --exclude-mode custom --exclude-keywords-file ./custom_exclusion_keywords.txt --delete
```

Custom whitespace-separated files treat `project` and `name` as two terms. Put multi-word phrases in a replacement JSON profile when phrase matching is required. Keep personalized files outside `site-packages` so package upgrades cannot overwrite them.

## Keywords On The Command Line

Use `--match-keywords` and `--exclude-keywords` for terms that do not need a file. Each shell argument is one term, so quote phrases and hashtags:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match custom --match-keywords hobby "family photo" "#memories" --exclude-keywords client "work project" "#portfolio" --delete
```

Inline terms augment a selected built-in profile. For example, this matches the built-in work profile plus `freelance`:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match work --match-keywords freelance --delete
```

Supplying `--exclude-keywords` without `--exclude-mode` automatically uses custom exclusion mode.

## All Options

```text
-h, --help              Show command help and exit.
--profile-url URL       X profile URL to scan. Required.
--max-posts N           Optional selected-item limit. Omit for the entire timeline.
--delete                Perform matched delete/undo actions. Omit for a dry run.
--headless              Run a launched browser without a visible window.
--browser NAME          Browser engine: chromium or firefox. Default: chromium.
--browser-profile-dir PATH
                        Persistent browser profile directory.
--browser-channel NAME  Chromium channel: chrome, chrome-beta, chrome-dev,
                        chrome-canary, msedge, or chromium.
--executable-path PATH  Browser executable to launch.
--connect-cdp URL       Attach to running Chrome/Chromium through CDP.
--login                 Open X login and wait for Enter before scanning.
--target TYPE           Selected category: posts, replies, or retweets.
--match MODE            Match personal, work, politics, custom, or all.
--delete-all            Interleave repost undo and owned post/reply deletion.
--delete-all-posts      Delete every original post regardless of content.
--delete-all-replies    Delete every reply regardless of content.
--delete-all-retweets   Undo every repost regardless of content.
--unretweet-all         Alias for --delete-all-retweets.
--include-replies       Deprecated alias for --target replies.
--match-keywords-file PATH
                        Add/customize match terms separated by spaces or newlines.
--keywords-file PATH    Compatibility alias for --match-keywords-file.
--exclude-keywords-file PATH
                        Add/customize exclusion terms separated by spaces or newlines.
--match-keywords TERM [TERM ...]
                        Add match terms directly; quote phrases and #hashtags.
--exclude-keywords TERM [TERM ...]
                        Add exclusion terms directly; quote phrases and #hashtags.
--keyword-profiles PATH JSON file containing personal, work, and politics profiles.
--only-keywords-file    Deprecated shortcut for --match custom.
--exclude-mode MODE     Preserve personal, work, politics, or custom matches.
--pause SECONDS         Delay between browser actions. Default: 0.8.
```

`--connect-cdp` cannot be combined with `--login`, `--headless`, `--browser-profile-dir`, `--browser-channel`, or `--executable-path`.

## Notes

- Run a dry-run command before selective deletion.
- `--target replies` uses the profile's `/with_replies` timeline.
- Reposts are removed by undoing your repost, never by deleting the original author's post.
- A matched stale repost marker with an available Repost action is temporarily reposted and then immediately unreposted.
- Reposts made by the logged-in account are undone regardless of who authored the original post.
- Every destructive action re-checks the item type immediately before clicking; an unverified item is skipped.
- Post ownership is verified from the profile handle in its `/HANDLE/status/...` permalink.
- Failed timeline deletions are retried from the owned post's permalink in a temporary tab.
- Exclusion profiles preserve matching owned posts/replies but do not preserve reposts.
- X changes its interface often. Missing menus or confirmation buttons are reported and skipped.
- Use this tool only on accounts you control.

## Development Structure

```text
pyproject.toml                  Build metadata, dependencies, and CLI entrypoints
custom_match_keywords.txt      Editable custom matching template
custom_exclusion_keywords.txt  Editable custom exclusion template
twit_cleaner/
  __main__.py                   Package entrypoint for python -m twit_cleaner
  keyword_profiles.json         Built-in personal, work, and politics profiles
  app.py                        Application orchestration and exit codes
  cli.py                        Arguments, shortcuts, and validation
  models.py                     Enums and immutable runtime models
  constants.py                  UI labels and project paths
  keywords.py                   Profile loading and text classification
  urls.py                       Profile and owned-status URL handling
  posts.py                      Timeline-card inspection and type decisions
  navigation.py                 Login and profile navigation
  actions.py                    Delete, permalink fallback, and unretweet actions
  scanner.py                    Sequential timeline scanning
  browser.py                    CDP and persistent-browser lifecycle
tests/
  test_domain.py                Ownership, mode, CLI, and keyword contracts
```

Internal modules use package-relative imports. Run the installed `twit-cleaner` command or invoke the package directly with `python -m twit_cleaner`.
