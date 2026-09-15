# Telegram Media Downloader Bot

Downloads video / audio / images from social links (TikTok, Instagram, Facebook,
YouTube, Twitter/X, and most other sites yt-dlp supports) and sends them back
in Telegram chat.

## 1. Create the bot

1. Open Telegram, message **@BotFather**.
2. Send `/newbot`, follow the prompts, and copy the token it gives you
   (looks like `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`).

## 2. Install dependencies

You also need **ffmpeg** installed on the machine (yt-dlp uses it to merge
video+audio and to convert to mp3).

```bash
# Debian/Ubuntu
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

pip install -r requirements.txt
```

## 3. Set your token and run

```bash
export BOT_TOKEN="123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
python bot.py
```

Open your bot in Telegram, send `/start`, then paste a link. It'll ask
whether you want the video, the audio (as MP3), or an image.

## Notes & limitations

- **Upload size**: the standard Telegram Bot API only allows bots to upload
  files up to **50 MB**. For bigger videos you'd need to run a local Bot API
  server (https://github.com/tdlib/telegram-bot-api) which raises the limit
  to 2 GB — that's a bigger setup step, ask if you want help with it.
- **Private/login-walled content**: Instagram and Facebook sometimes require
  a logged-in session to fetch certain posts (especially private accounts or
  Stories). yt-dlp supports passing browser cookies via `cookiesfrombrowser`
  or a `cookies.txt` file if you hit that — see the yt-dlp docs.
- **Platform changes**: TikTok/Instagram/Facebook change their internal APIs
  fairly often, which can break extraction until yt-dlp is updated. Keep
  `yt-dlp` upgraded (`pip install -U yt-dlp`) if downloads start failing.
- **Terms of Service**: downloading and especially redistributing content
  from these platforms may violate their ToS or copyright, depending on the
  content and how you use it. This tool is best suited for personal
  archiving of your own content or content you have rights to use.

## Deploying to GitHub + Railway (24/7 hosting)

This repo includes a `Dockerfile` and `railway.json` so Railway builds and
runs it automatically — no server setup needed.

### 1. Push the code to GitHub

```bash
cd telegram-media-bot
git init
git add .
git commit -m "Initial commit: Telegram media downloader bot"
```

Create a new empty repo on GitHub (github.com/new — don't initialize it with
a README), then:

```bash
git remote add origin https://github.com/<your-username>/<your-repo>.git
git branch -M main
git push -u origin main
```

Your `.gitignore` already excludes `.env` and other local junk, so your
token won't be committed as long as you keep it out of `bot.py` (the code
reads it from an environment variable, not a hardcoded value).

### 2. Deploy on Railway

1. Go to [railway.app](https://railway.app) and sign in (you can sign in
   with your GitHub account directly).
2. Click **New Project → Deploy from GitHub repo**, and pick the repo you
   just pushed. Authorize Railway to access it if prompted.
3. Railway will detect the `Dockerfile` and build the image automatically
   (this installs ffmpeg + the Python deps for you).
4. Go to your new service → **Variables** tab → add:
   - `BOT_TOKEN` = your token from BotFather
5. Go to the **Deployments** tab and confirm it deploys successfully — check
   the logs for `Bot started. Waiting for messages...`.

That's it — the bot now runs continuously on Railway. Since it uses polling
(not a webhook), it doesn't need a public URL or port exposed.

### 3. Redeploying after changes

Any time you `git push` to `main`, Railway automatically rebuilds and
redeploys the service (this is Railway's default behavior for GitHub-linked
projects — no extra config needed).

### Notes on Railway specifically

- **Free tier limits**: Railway's free tier has a monthly usage credit and
  will pause the service once you exceed it — check your current plan's
  limits on their pricing page if the bot stops responding.
- **Persistent storage**: this bot downloads to a temp folder and deletes
  it after sending, so it doesn't need a persistent volume. If you later add
  features like download history, you'd want a Railway volume or an
  external database (their storage resets on redeploy otherwise).
- **Logs**: Railway's dashboard shows live logs, which is the easiest way to
  debug download failures without SSHing anywhere.

## Alternative: running on your own VPS

If you'd rather not use Railway:

```bash
pip install -r requirements.txt
nohup python bot.py &> bot.log &
```

Or use the included `Dockerfile` directly with plain Docker:

```bash
docker build -t media-bot .
docker run -d --env BOT_TOKEN=your_token_here --restart unless-stopped media-bot
```
