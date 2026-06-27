# Twit Cleaner

A Playwright browser-navigation tool for deleting posts and replies from your own X account and undoing your reposts. Political matching is keyword based. Scans are unlimited unless `--max-posts` is supplied.

## Project Structure

```text
pyproject.toml              Build metadata, dependencies, and CLI entrypoints
twit_cleaner/
  __main__.py               Package entrypoint for python -m twit_cleaner
  keyword_profiles.json     Bundled political terms and exclusion profiles
  app.py                    Application orchestration and exit codes
  cli.py                    Arguments, shortcuts, and validation
  models.py                 Enums and immutable runtime models
  constants.py              UI labels and project paths
  keywords.py               Profile loading and text classification
  urls.py                   Profile and owned-status URL handling
  posts.py                  Timeline-card inspection and type decisions
  navigation.py             Login and profile navigation
  actions.py                Delete, permalink fallback, and unretweet actions
  scanner.py                Sequential timeline scanning
  browser.py                CDP and persistent-browser lifecycle
tests/
  test_domain.py            Ownership, mode, CLI, and keyword contracts
```

Internal modules use package-relative imports. Run the installed `twit-cleaner` command or invoke the package directly with `python -m twit_cleaner`.

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

**Unsafe and irreversible:** this command makes one interleaved pass through `/with_replies`. For each card, it undoes an active repost or deletes the card when its primary permalink belongs to your profile. It does not inspect political content and does not ask for confirmation in the terminal. X still displays its normal per-item confirmation dialog, which the tool accepts automatically.

With your remote-debugging Chrome window open and logged in, run:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all
```

Reposts, replies, and original posts are handled in the order they appear. Each item is processed sequentially: find one, choose Undo repost or Delete, act on it, query the updated `/with_replies` timeline, then find the next one. If one of your own posts is also reposted, the tool undoes the repost first, then sees the same owned permalink again and deletes the post. Press `Ctrl+C` to stop.

Before every removal, the tool checks for an active `unretweet` control. That control means your logged-in account reposted the item; the original post may belong to any account. Those items use **Undo repost** without requiring the original author's permalink to match your handle. Only post and reply deletion requires a permalink matching `/YOUR_HANDLE/status/...`, which prevents conversation cards from other accounts from being deleted. The tool first tries the timeline menu; if that fails, it opens the owned permalink in a temporary tab and retries there.

## Exclusion Modes

Exclusion modes preserve owned posts and replies containing configured words or hashtags. They do not prevent the tool from undoing your reposts.

- `--exclude-mode personal` keeps content matching the `personal` profile.
- `--exclude-mode work` keeps content matching the `work` profile.
- `--exclude-mode custom` keeps content matching your personalized `custom` profile.

All terms are stored in [`twit_cleaner/keyword_profiles.json`](twit_cleaner/keyword_profiles.json), outside the Python code. The `custom` profile intentionally starts with blank `keywords` and `hashtags` lists. In a source checkout, edit those lists to personalize what the tool should preserve:

```json
"custom": {
  "keywords": ["my project", "family name"],
  "hashtags": ["keepme", "portfolio"]
}
```

Then add the custom exclusion mode to the delete-all command:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all --exclude-mode custom
```

Keywords are case-insensitive. Hashtags may be written with or without `#` in the JSON file.

For a pip-installed copy, keep your personalized JSON outside `site-packages` and pass it with `--keyword-profiles PATH`. This prevents upgrades from replacing your customization.

## Political Command Examples

Dry-run all political posts without deleting anything:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match politics
```

Delete all political posts:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match politics --delete
```

Delete all political replies:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target replies --match politics --delete
```

Undo all political reposts:

```bash
twit-cleaner --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target retweets --match politics --delete
```

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
--match MODE            Matching mode: politics or all. Default: politics.
--delete-all            Interleave repost undo and owned post/reply deletion.
--delete-all-posts      Delete every original post regardless of content.
--delete-all-replies    Delete every reply regardless of content.
--delete-all-retweets   Undo every repost regardless of content.
--unretweet-all         Alias for --delete-all-retweets.
--include-replies       Deprecated alias for --target replies.
--keywords-file PATH    Add keywords from a text file, one term per line.
--keyword-profiles PATH JSON file containing political and exclusion profiles.
--only-keywords-file    Use only --keywords-file terms; ignore built-ins.
--exclude-mode MODE     Preserve matches from personal, work, or custom.
--pause SECONDS         Delay between browser actions. Default: 0.8.
```

`--connect-cdp` cannot be combined with `--login`, `--headless`, `--browser-profile-dir`, `--browser-channel`, or `--executable-path`.

## Notes

- Run a dry-run command before selective political deletion.
- `--target replies` uses the profile's `/with_replies` timeline.
- Reposts are removed by undoing your repost, never by deleting the original author's post.
- Reposts made by the logged-in account are undone regardless of who authored the original post.
- Every destructive action re-checks the item type immediately before clicking; an unverified item is skipped.
- Post ownership is verified from the profile handle in its `/HANDLE/status/...` permalink.
- Failed timeline deletions are retried from the owned post's permalink in a temporary tab.
- Exclusion profiles preserve matching owned posts/replies but do not preserve reposts.
- X changes its interface often. Missing menus or confirmation buttons are reported and skipped.
- Use this tool only on accounts you control.

## Keyword Profiles

The complete political keyword list, political hashtag list, personal exclusions, work exclusions, and blank custom profile are maintained in [`twit_cleaner/keyword_profiles.json`](twit_cleaner/keyword_profiles.json). Use `--keyword-profiles PATH` to load a different profile file.
