# Google Play API — Service Account Setup (required for MCP + upload script)

The LobeHub / Blocktopus Google Play MCP and `scripts/upload_play_aab.mjs` both need a **Google Cloud service account JSON** linked to your Play Console.

Without this file, Cursor cannot talk to Play Console or upload an AAB.

## 1. Enable the API

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project (e.g. `pest99-play-api`)
3. **APIs & Services → Library** → search **Google Play Android Developer API** → **Enable**

## 2. Create the service account

1. **IAM & Admin → Service Accounts → Create service account**
2. Name: `play-console-uploader`
3. Skip optional roles (Play uses Play Console permissions, not GCP IAM roles)
4. Open the service account → **Keys → Add key → Create new key → JSON**
5. Download the JSON file

## 3. Invite it in Play Console

1. Open [Google Play Console](https://play.google.com/console)
2. **Users and permissions → Invite new users**
3. Paste the service account **email** (`…@….iam.gserviceaccount.com`)
4. Permissions (minimum for deploy):
   - **View app information and download bulk reports**
   - **Manage store presence** (if updating listing via MCP)
   - **Release apps to testing tracks** (internal / closed / open)
   - Optionally **Release to production** later
5. App access: grant access to **Pest Control99 Partner** (`com.multipestcare.partner`)
6. Send invite / save

Wait a few minutes after inviting (API access can lag).

## 4. Place the key for Cursor

Save the downloaded JSON as:

```text
/Users/adnanshaikh/.config/pest99/google-play-service-account.json
```

Do **not** put this file inside the git repo.

## 5. Reload MCP in Cursor

Project MCP config (`.cursor/mcp.json`) already points at that path using package:

```text
@blocktopus/mcp-google-play
```

(LobeHub lists identifier `blocktopusltd-mcp-google-play`, but the real npm package is `@blocktopus/mcp-google-play`.)

Reload MCP servers in Cursor (or restart Cursor), then ask the agent to `list_releases` / upload.

## 6. Upload AAB (MCP cannot upload binaries)

The Blocktopus MCP can update listings and create releases from an **already uploaded** versionCode.  
To upload the `.aab` file itself, run:

```bash
cd "pest_99_partner_app"
npm install googleapis --no-save
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/pest99/google-play-service-account.json"
node scripts/upload_play_aab.mjs \
  --aab Pest99-Partner-PlayStore-v2.0.5.aab \
  --track internal \
  --notes "Internal test v2.0.5"
```

## Play Console dashboard blockers (from your screenshot)

Before **Closed / Open / Production** unlock:

1. Complete **Set up your app** (store listing, app content, etc.) — see `PLAY_STORE_LISTING.md` and `PLAY_CONSOLE_SETUP.md`
2. Prefer first release on **Internal testing**

Package name must stay: `com.multipestcare.partner`
