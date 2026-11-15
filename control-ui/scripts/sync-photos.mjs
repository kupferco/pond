// Copies new or changed images from the Drive folder "Pond photos" into Cloud Storage
// (photos/web/<id>.jpg, photos/thumb/<id>.jpg, photos/index.json). Idempotent: a file is skipped when its
// Drive id is already in the index with the same modifiedTime. Files removed from the folder are removed
// from the bucket. Run:  node scripts/sync-photos.mjs   (see docs/notes/2026-11-14-photos.md)
//
// Env: GOOGLE_APPLICATION_CREDENTIALS (service account key file), PHOTOS_BUCKET (default pond-grow.firebasestorage.app),
//      PHOTOS_FOLDER_ID (optional; otherwise the folder named "Pond photos" shared with the service account),
//      PHOTOS_DRIVE_ID (optional; id of the shared drive, to search only that one),
//      DRY_RUN=1 to only print what would happen.
import { google } from 'googleapis';
import { Storage } from '@google-cloud/storage';
import sharp from 'sharp';

const BUCKET = process.env.PHOTOS_BUCKET || 'pond-grow.firebasestorage.app';
const DRY = !!process.env.DRY_RUN;
const WEB_PX = 1600, THUMB_PX = 400;
const FOLDER_NAME = 'Pond photos';

// Works for shared drives and My Drive: every list/get passes supportsAllDrives; lists also search all drives
// the service account can see (or only PHOTOS_DRIVE_ID, if set).
const ALL_DRIVES = {
  supportsAllDrives: true, includeItemsFromAllDrives: true,
  ...(process.env.PHOTOS_DRIVE_ID ? { corpora: 'drive', driveId: process.env.PHOTOS_DRIVE_ID } : { corpora: 'allDrives' }),
};

const auth = new google.auth.GoogleAuth({ scopes: ['https://www.googleapis.com/auth/drive.readonly'] });
const drive = google.drive({ version: 'v3', auth });
const bucket = new Storage().bucket(BUCKET);

async function findFolder() {
  if (process.env.PHOTOS_FOLDER_ID) return process.env.PHOTOS_FOLDER_ID;
  const r = await drive.files.list({
    q: `mimeType='application/vnd.google-apps.folder' and name='${FOLDER_NAME}' and trashed=false`,
    fields: 'files(id,name)', ...ALL_DRIVES,
  });
  const f = r.data.files || [];
  if (!f.length) throw new Error(`No folder "${FOLDER_NAME}" visible to the service account. Add the service account's email (Viewer) to the shared drive or the folder.`);
  if (f.length > 1) console.warn(`${f.length} folders named "${FOLDER_NAME}" are shared; using the first. Set PHOTOS_FOLDER_ID to pick one.`);
  return f[0].id;
}

async function listImages(folderId) {
  const out = [];
  let pageToken;
  do {
    const r = await drive.files.list({
      q: `'${folderId}' in parents and mimeType contains 'image/' and trashed=false`,
      fields: 'nextPageToken,files(id,name,description,mimeType,modifiedTime,createdTime,imageMediaMetadata(time))',
      pageSize: 200, pageToken, ...ALL_DRIVES,
    });
    out.push(...(r.data.files || []));
    pageToken = r.data.nextPageToken;
  } while (pageToken);
  return out;
}

// EXIF time looks like "2024:05:17 14:03:22"; fall back to the Drive creation time.
function takenDate(f) {
  const t = f.imageMediaMetadata?.time;
  const m = t && /^(\d{4}):(\d\d):(\d\d) (\d\d):(\d\d):(\d\d)$/.exec(t);
  return m ? `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}` : f.createdTime;
}

async function readIndex() {
  const file = bucket.file('photos/index.json');
  if ((await file.exists())[0]) return JSON.parse((await file.download())[0].toString('utf8'));
  return { photos: [] };
}

async function put(path, buf, contentType) {
  await bucket.file(path).save(buf, { contentType, metadata: { cacheControl: 'public, max-age=3600' } });
}

const old = await readIndex();
const known = new Map(old.photos.map(p => [p.id, p]));
const files = await listImages(await findFolder());
const seen = new Set();
const photos = [];
let added = 0, updated = 0, skipped = 0, failed = 0;

for (const f of files) {
  seen.add(f.id);
  const prev = known.get(f.id);
  const meta = { id: f.id, name: f.name, caption: f.description || '', taken: takenDate(f), modified: f.modifiedTime };
  if (prev && prev.modified === f.modifiedTime) {
    photos.push({ ...prev, name: meta.name, caption: meta.caption }); // name/description edits don't need a re-copy
    skipped++;
    continue;
  }
  console.log(`${prev ? 'update' : 'add'}: ${f.name}`);
  if (DRY) { photos.push(meta); prev ? updated++ : added++; continue; }
  try {
    const res = await drive.files.get({ fileId: f.id, alt: 'media', supportsAllDrives: true }, { responseType: 'arraybuffer' });
    const src = sharp(Buffer.from(res.data)).rotate(); // apply EXIF orientation
    const web = await src.clone().resize({ width: WEB_PX, height: WEB_PX, fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 82, mozjpeg: true }).toBuffer({ resolveWithObject: true });
    const thumb = await src.clone().resize({ width: THUMB_PX, height: THUMB_PX, fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 75 }).toBuffer();
    await put(`photos/web/${f.id}.jpg`, web.data, 'image/jpeg');
    await put(`photos/thumb/${f.id}.jpg`, thumb, 'image/jpeg');
    photos.push({ ...meta, w: web.info.width, h: web.info.height });
    prev ? updated++ : added++;
  } catch (e) {
    console.error(`failed: ${f.name}: ${e.message}`);
    failed++;
    if (prev) photos.push(prev); // keep the old copy
  }
}

let removed = 0;
for (const p of old.photos) {
  if (seen.has(p.id)) continue;
  console.log(`remove: ${p.name}`);
  removed++;
  if (!DRY) await Promise.all([`photos/web/${p.id}.jpg`, `photos/thumb/${p.id}.jpg`].map(n => bucket.file(n).delete({ ignoreNotFound: true })));
}

photos.sort((a, b) => (b.taken || '').localeCompare(a.taken || ''));
if (!DRY) await put('photos/index.json', Buffer.from(JSON.stringify({ updated: new Date().toISOString(), photos })), 'application/json');
console.log(`${DRY ? '[dry run] ' : ''}added ${added}, updated ${updated}, unchanged ${skipped}, removed ${removed}, failed ${failed}; ${photos.length} photos total`);
if (failed) process.exitCode = 1;
