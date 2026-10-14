# Deep-Quote Instagram Bot

Completely free to run. Posts one original, AI-written quote every evening as a minimal dark image, with a caption written to start conversations and a rotating hashtag set. A weekly report shows what's working. Everything runs free on GitHub Actions, and it only uses Instagram's official API. It never needs your password.

## What it does

| When | What |
|---|---|
| Daily, ~19:17 IST | Gemini (free) writes a fresh quote on a rotating theme (it checks history so quotes never repeat). The bot renders a 1080×1350 image and builds the caption + 12 hashtags, then publishes. |
| Sunday morning | Refreshes the Instagram token (it would otherwise expire after 60 days) and writes `reports/<date>.md` with reach, saves, shares, top posts and your best posting hours. |

## Cost: ₹0

| Piece | Cost |
|---|---|
| GitHub repo + Actions (public repo) | Free, unlimited minutes |
| Instagram API (Meta developer app) | Free |
| Quote writing: Google Gemini free tier | Free, no card |
| Fallback: built-in 60-quote bank | Free, no key at all |
| Fonts (Playfair Display, Inter) | Free, open licence |

Optional upgrade: add an `ANTHROPIC_API_KEY` secret to use Claude instead (paid, a few rupees a month).

## One-time setup (~20 minutes)

### 1. Make the Instagram account Professional
Instagram app → Settings → *Account type and tools* → **Switch to professional account** → choose **Creator** (or Business). It's free and you can switch back.

### 2. Create a Meta app and get a token
1. Go to <https://developers.facebook.com/apps> → **Create app** → use case **"Manage messaging & content on Instagram"**.
2. In the app: **Instagram → API setup with Instagram login**.
3. Under *Generate access tokens* click **Add account** and log in to your Instagram **there, on Meta's own page**. Approve the permissions:
   `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_insights`.
4. Click **Generate token**. Copy the token (this is a long-lived token, valid 60 days; the weekly job keeps renewing it).
5. Get your user id: open
   `https://graph.instagram.com/v23.0/me?fields=user_id,username&access_token=YOUR_TOKEN`
   and copy `user_id`.

> While the app is in *Development* mode it can still post to **your own** account (you're the app's admin/tester). You don't need App Review for that.

### 3. Get a free Google Gemini API key
<https://aistudio.google.com/apikey> → sign in with any Google account → **Create API key**. No credit card needed. One quote a day is far below the free-tier limit.
(If you skip this, the bot uses its built-in bank of 60 original quotes, which covers two months with zero keys.)

### 4. Put the code on GitHub
1. Create a **public** repository (Instagram must be able to download the image from `raw.githubusercontent.com`; only quote images live there).
2. Upload everything in this folder (including the `.github` folder) to it.
3. Edit `config.yaml`: set `page_handle`, and tweak themes/hashtags if you like.

### 5. Add repository secrets
Repo → Settings → Secrets and variables → Actions → **New repository secret**:

| Secret | Value |
|---|---|
| `IG_ACCESS_TOKEN` | token from step 2 |
| `IG_USER_ID` | user_id from step 2 |
| `GEMINI_API_KEY` | free key from step 3 |
| `GH_PAT` | a [fine-grained token](https://github.com/settings/personal-access-tokens/new) for **this repo only**, permission **Secrets: Read and write** (lets the weekly job save the refreshed Instagram token) |

### 6. Test
Actions tab → **Daily quote post** → **Run workflow**. Check Instagram a minute later. Then run **Weekly insights + token refresh** once to confirm the token refresh works.

## Run locally (optional)
```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...         # optional
python main.py post --dry-run     # writes posts/<date>.jpg + prints caption, no posting
```

## Growing reach: what actually helps
The bot handles consistency, timing, hashtags and comment-inviting captions. These are the things worth doing by hand:
- **Reply to every comment in the first hour.** Early conversation is a strong ranking signal.
- **Saves and shares matter more than likes.** The weekly report ranks posts by them, so ask Claude for more quotes like your top ones by adding those themes to `config.yaml`.
- **Share each post to your Story** (one tap in the app) and occasionally turn a top quote into a Reel.
- **Engage genuinely** with 5–10 similar pages a day for a few minutes.
- **Avoid** follow/unfollow bots, engagement pods, bought followers and "growth services". Instagram detects them and they lead to shadowbans.

## Changing things
- **Post time:** edit the `cron` line in `.github/workflows/daily-post.yml` (it's in UTC; IST = UTC + 5:30).
- **Look:** colors in `config.yaml`, layout in `src/render.py`.
- **Voice of the quotes:** the prompt in `src/generate.py`.
- **Pause:** Actions tab → the workflow → ⋯ → Disable workflow.
