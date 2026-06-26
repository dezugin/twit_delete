# Twit Delete

Browser-navigation tool for reviewing and removing posts, replies, and reposts from your own X account. It scans the entire selected timeline by default.

The normal commands are dry runs. Destructive commands use `--delete` or one of the explicit `--delete-all-*` shortcuts.

## Delete All Posts, Replies, And Reposts

This is the first and most destructive option. It deletes every post and reply and undoes every repost, regardless of political content. Make sure the Chrome window started with remote debugging is open and logged in, then run:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --delete-all
```

The command starts on the combined Posts and Replies timeline so it can delete the first eligible item immediately, instead of scrolling through a Posts-only pass first. It finds one item, removes it, refreshes its view, and then finds the next. Afterward, it makes a separate pass to undo reposts. It does not classify or preview political content in this mode. Use `Ctrl+C` to stop it.

## Setup

```bash
cd ~/Documents/twbot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium firefox
```

## Use Your Logged-In Chrome Window

Chrome must be started with remote debugging and a non-default data directory. Start it with this complete command:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-x-cdp" --ozone-platform=x11
```

For Chromium, use:

```bash
chromium --remote-debugging-port=9222 --user-data-dir="$HOME/.chromium-x-cdp" --ozone-platform=x11
```

Log in to X in that browser and leave it open. Confirm that the connection is available:

```bash
curl http://127.0.0.1:9222/json/version
```

The commands below attach to that browser. Replace `dezugin` if you want to operate on a different account you control.

## Dry Run: Political Content

Inspect all political posts without deleting:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target posts --match politics
```

Inspect all political replies without deleting:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target replies --match politics
```

Inspect all political reposts without undoing them:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target retweets --match politics
```

## Delete Political Content

Delete all political posts:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target posts --match politics --delete
```

Delete all political replies:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target replies --match politics --delete
```

Undo all political reposts:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target retweets --match politics --delete
```

## Dry Run: Everything In One Category

Inspect every post without deleting:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target posts --match all
```

Inspect every reply without deleting:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target replies --match all
```

Inspect every repost without undoing it:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --target retweets --match all
```

## Delete Everything In One Category

These commands are destructive and scan the entire corresponding timeline.

The `--delete-all-*` commands skip political-content classification and immediately remove each item found in the selected category.

Delete every post, regardless of content:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --delete-all-posts
```

Delete every reply, regardless of content:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --delete-all-replies
```

Undo every repost/retweet, regardless of content:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --delete-all-retweets
```

To remove everything from all three categories, run all three commands above. X exposes posts, replies, and reposts through different timeline views, so the tool handles them as separate actions.

## Separate Playwright Browser Login

If you do not want to attach to Chrome, open a dedicated persistent browser and log in:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --login
```

The Chromium session is saved in `.browser-profile/`. Later commands can omit `--login`:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --target posts --match politics
```

For a dedicated Firefox session:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --browser firefox --login
```

Playwright cannot reliably attach to a normal Firefox window that is already open.

## Options

```text
--profile-url URL        X profile URL to scan.
--max-posts N           Optional scan cap. Omit it to scan the entire timeline.
--delete                Perform deletion/undo actions. Omit it for a dry run.
--headless              Run without showing the browser.
--browser BROWSER       Use chromium or firefox. Default: chromium.
--browser-profile-dir   Persistent browser profile directory to use.
--browser-channel       Installed Chromium-family channel, such as chrome.
--executable-path       Browser executable to launch.
--connect-cdp URL       Attach to Chrome/Chromium through remote debugging.
--login                 Open X login and wait for Enter before scanning.
--target TYPE           Scan posts, replies, or retweets. Default: posts.
--match MODE            Match politics or all. Default: politics.
--delete-all            Delete all posts/replies and undo all reposts.
--delete-all-posts      Delete all posts regardless of content.
--delete-all-replies    Delete all replies regardless of content.
--delete-all-retweets   Undo all reposts regardless of content.
--keywords-file PATH    Add or replace political keywords from a text file.
--only-keywords-file    Ignore built-in keywords and use only the file.
--pause SECONDS         Delay between browser actions.
```

## Notes

- Omit `--max-posts` to continue until X stops returning new timeline cards. There is no default 100-post cap.
- Items are handled sequentially: find one, act on it, then query the updated timeline for the next one.
- `--target replies` scans the profile's `/with_replies` view and treats visible non-repost cards there as replies.
- Reposts are removed by undoing your repost, not by deleting the original author's post.
- X changes its interface often. If a menu or confirmation button is missing, the tool reports and skips that item.
- Use this only on accounts you control, and run the matching dry-run command before destructive cleanup.
