# Twitter/X Political Post Cleaner

Browser-navigation bot that reviews posts on your own X profile and deletes them. Option to delete the ones that look political, based on chosen keywords.

It uses Playwright to drive a real browser session, so you can log in manually and keep the session in a local browser profile. Deletion is off by default: run a dry run first, inspect the matches, then opt in with `--delete`.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## First Run

Open a visible browser and log in when prompted:

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all
```

The bot stores the browser session in `.browser-profile/`.

## Delete all posts

```bash
python twit_delete.py --profile-url https://x.com/YOUR_HANDLE --connect-cdp http://127.0.0.1:9222 --delete-all
```

## Delete Matching Posts

```bash
python tw_delete_politics.py --profile-url https://x.com/YOUR_HANDLE --max-posts 50 --delete
```

## Options

```text
--profile-url URL        Your X/Twitter profile URL.
--max-posts N           Stop after scanning this many post cards.
--delete                Actually delete matching posts. Without this, it only reports.
--headless              Run without showing the browser. Use only after login works.
--keywords-file PATH    Add or replace political keywords from a text file.
--only-keywords-file    Use only the keyword file and ignore built-in keywords.
--pause SECONDS         Delay between actions.
```

## Notes

- The classifier is keyword based. It intentionally favors caution, but you should still dry-run first.
- The UI of X changes often. If a menu or delete button is not found, the bot skips that post instead of forcing clicks.
- Use this only on accounts you control.
