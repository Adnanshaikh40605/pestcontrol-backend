#!/usr/bin/env node
/**
 * Upload a signed AAB to Google Play (internal track by default).
 *
 * Why this exists: @blocktopus/mcp-google-play can create releases and
 * update listings, but it does NOT upload APK/AAB binaries. This script
 * uses the Play Developer API edits.bundles.upload + tracks.update flow.
 *
 * Usage:
 *   export GOOGLE_APPLICATION_CREDENTIALS=~/.config/pest99/google-play-service-account.json
 *   node scripts/upload_play_aab.mjs \
 *     --aab Pest99-Partner-PlayStore-v2.0.5.aab \
 *     --package com.pestcontrol99.partner \
 *     --track internal \
 *     --notes "Initial internal test build"
 *
 * Optional: --status draft|completed  (default: completed)
 */
import { createReadStream, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { google } from 'googleapis';

function parseArgs(argv) {
  const out = {
    aab: null,
    package: 'com.pestcontrol99.partner',
    track: 'internal',
    notes: 'Pest 99 Partner internal test release',
    status: 'completed',
    language: 'en-US',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--aab') out.aab = argv[++i];
    else if (a === '--package') out.package = argv[++i];
    else if (a === '--track') out.track = argv[++i];
    else if (a === '--notes') out.notes = argv[++i];
    else if (a === '--status') out.status = argv[++i];
    else if (a === '--language') out.language = argv[++i];
    else if (a === '--help' || a === '-h') out.help = true;
  }
  return out;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help || !opts.aab) {
    console.log(`Usage: node scripts/upload_play_aab.mjs --aab <file.aab> [options]
  --package  default com.pestcontrol99.partner
  --track    internal|alpha|beta|production  (default internal)
  --notes    release notes
  --status   draft|completed  (default completed)
Requires GOOGLE_APPLICATION_CREDENTIALS pointing at a Play Console service account JSON.`);
    process.exit(opts.help ? 0 : 1);
  }

  const keyFile = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (!keyFile || !existsSync(keyFile)) {
    console.error(
      'Missing GOOGLE_APPLICATION_CREDENTIALS (service account JSON). See docs/PLAY_API_SERVICE_ACCOUNT.md'
    );
    process.exit(1);
  }

  const aabPath = resolve(opts.aab);
  if (!existsSync(aabPath)) {
    console.error(`AAB not found: ${aabPath}`);
    process.exit(1);
  }

  const auth = new google.auth.GoogleAuth({
    keyFile,
    scopes: ['https://www.googleapis.com/auth/androidpublisher'],
  });
  const authClient = await auth.getClient();
  const androidpublisher = google.androidpublisher({
    version: 'v3',
    auth: authClient,
  });

  const packageName = opts.package;
  console.log(`Creating edit for ${packageName}...`);
  const edit = await androidpublisher.edits.insert({ packageName });
  const editId = edit.data.id;
  if (!editId) throw new Error('No editId returned');

  console.log(`Uploading AAB: ${aabPath}`);
  const upload = await androidpublisher.edits.bundles.upload({
    packageName,
    editId,
    media: {
      mimeType: 'application/octet-stream',
      body: createReadStream(aabPath),
    },
  });

  const versionCode = upload.data.versionCode;
  console.log(`Uploaded versionCode=${versionCode}`);

  console.log(`Assigning to track=${opts.track} status=${opts.status}`);
  await androidpublisher.edits.tracks.update({
    packageName,
    editId,
    track: opts.track,
    requestBody: {
      track: opts.track,
      releases: [
        {
          name: `v${versionCode}`,
          versionCodes: [String(versionCode)],
          status: opts.status,
          releaseNotes: [
            {
              language: opts.language,
              text: opts.notes,
            },
          ],
        },
      ],
    },
  });

  console.log('Committing edit...');
  const commit = await androidpublisher.edits.commit({ packageName, editId });
  console.log(
    JSON.stringify(
      {
        ok: true,
        packageName,
        track: opts.track,
        versionCode,
        editId: commit.data.id,
      },
      null,
      2
    )
  );
}

main().catch((err) => {
  console.error(err?.response?.data || err);
  process.exit(1);
});
