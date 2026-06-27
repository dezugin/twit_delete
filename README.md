# Twit Delete

A Playwright browser-navigation tool for deleting posts and replies from your own X account and undoing your reposts. Political matching is keyword based. Scans are unlimited unless `--max-posts` is supplied.

## Warning: Delete Everything

**Unsafe and irreversible:** this command deletes every post and reply it can find and undoes every repost. It does not inspect political content and does not ask for confirmation in the terminal. X still displays its normal per-item confirmation dialog, which the tool accepts automatically.

With your remote-debugging Chrome window open and logged in, run:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all
```

Items are handled sequentially: find one, remove it, query the updated timeline, then find the next one. Press `Ctrl+C` to stop.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium firefox
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

## Command Examples

Dry-run all political posts without deleting anything:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match politics
```

Delete _all_ posts:

```bash
python twit_delete.py --profile-url https://x.com/dezugin --connect-cdp http://127.0.0.1:9222 --delete-all
```

Delete all political posts:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match politics --delete
```

Delete all political replies:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target replies --match politics --delete
```

Undo all political reposts:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target retweets --match politics --delete
```

Dry-run every reply regardless of content:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target replies --match all
```

Delete every original post regardless of content:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all-posts
```

Delete every reply regardless of content:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all-replies
```

Undo every repost regardless of content:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all-retweets
```

Test only the first 25 selected items:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match politics --max-posts 25
```

Add political terms from `keywords.txt` to the built-in keywords:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match politics --keywords-file keywords.txt
```

Use only terms from `keywords.txt`, ignoring all built-in keywords and hashtags:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --target posts --match politics --keywords-file keywords.txt --only-keywords-file
```

Open a separate persistent Chromium session and pause for manual login:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --login
```

Use a dedicated Firefox session:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --browser firefox --login
```

Run a logged-in persistent session headlessly with a slower action delay:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --headless --target posts --match politics --pause 1.5
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
--delete-all            Delete posts/replies and undo reposts without classification.
--delete-all-posts      Delete every original post regardless of content.
--delete-all-replies    Delete every reply regardless of content.
--delete-all-retweets   Undo every repost regardless of content.
--include-replies       Deprecated alias for --target replies.
--keywords-file PATH    Add keywords from a text file, one term per line.
--only-keywords-file    Use only --keywords-file terms; ignore built-ins.
--pause SECONDS         Delay between browser actions. Default: 0.8.
```

`--connect-cdp` cannot be combined with `--login`, `--headless`, `--browser-profile-dir`, `--browser-channel`, or `--executable-path`.

## Notes

- Run a dry-run command before selective political deletion.
- `--target replies` uses the profile's `/with_replies` timeline.
- Reposts are removed by undoing your repost, never by deleting the original author's post.
- X changes its interface often. Missing menus or confirmation buttons are reported and skipped.
- Use this tool only on accounts you control.

## Built-In Political Keywords

Matching is case-insensitive. Multi-word terms are matched as phrases.

```text
abortion
biden
bolsonaro
brasil
brazil
congress
conservative
democrat
democratic
direita
election
electoral
esquerda
fascism
fascist
governador
governor
impeachment
leftist
liberal
lula
maga
mayor
minister
ministro
parliament
politica
política
president
prime minister
progressive
republican
right-wing
russia
senate
senator
socialism
socialist
stf
supreme court
trump
ukraine
vaccine mandate
white house
```

## Built-In Political Hashtags

```text
#biden2024
#bolsonaro
#democrats
#elections
#eleicoes
#fakenews
#fora
#impeachment
#lula
#maga
#politica
#politics
#republicans
#trump2024
```
