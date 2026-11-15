// Copies new or changed images from one Drive folder into Cloud Storage
// (photos/web/<id>.jpg, photos/thumb/<id>.jpg, photos/index.json). Idempotent: a file is skipped when its
// Drive id is already in the index with the same modifiedTime. Files removed from the folder are removed
// from the bucket. Only images directly in the folder are synced (videos, other files and subfolders are skipped).
// Run:  node scripts/sync-photos.mjs   (see docs/notes/2026-11-14-photos.md)
//
// Env: GOOGLE_APPLICATION_CREDENTIALS (service account key file), PHOTOS_BUCKET (default pond-grow.firebasestorage.app),
//      POND_PHOTOS_FOLDER_ID (preferred: Drive id of the folder to sync, from its URL),
//      POND_PHOTOS_FOLDER_PATH (fallback when no id is set; "/"-separated names, the first one being a shared drive
//      or a top-level folder; default "Pond 2.0/Images and Videos/Online Gallery/Pond 1.0"),
//      DRY_RUN=1 to only print what would happen.
import { google } from 'googleapis';
import { Storage } from '@google-cloud/storage';
import sharp from 'sharp';

const BUCKET = process.env.PHOTOS_BUCKET || 'pond-grow.firebasestorage.app';
const DRY = !!process.env.DRY_RUN;
const WEB_PX = 1600, THUMB_PX = 400;
const FOLDER_PATH = (process.env.POND_PHOTOS_FOLDER_PATH || 'Pond 2.0/Images and Videos/Online Gallery/Pond 1.0').split('/').map(x => x.trim()).filter(Boolean);

// Works for shared drives and My Drive: every list/get passes supportsAllDrives; lists also include shared drive items.
const ALL_DRIVES = { supportsAllDrives: true, includeItemsFromAllDrives: true };
const q = v => v.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
const FOLDER = "mimeType='application/vnd.google-apps.folder' and trashed=false";

const auth = new google.auth.GoogleAuth({ scopes: ['https://www.googleapis.com/auth/drive.readonly'] });
const drive = google.drive({ version: 'v3', auth });
const bucket = new Storage().bucket(BUCKET);

async function findFolder() {
  const id = (process.env.POND_PHOTOS_FOLDER_ID || '').trim();
  if (id) return id;
  const label = FOLDER_PATH.join(' / ');
  // First segment: a shared drive by that name, otherwise a top-level folder visible to the service account.
  const [first, ...rest] = FOLDER_PATH;
  const drives = (await drive.drives.list({ q: `name='${q(first)}'`, fields: 'drives(id)', pageSize: 10 })).data.drives || [];
  let parent, corpus;
  if (drives.length) {
    parent = drives[0].id; corpus = { corpora: 'drive', driveId: parent };
  } else {
    const r = await drive.files.list({ q: `${FOLDER} and name='${q(first)}'`, fields: 'files(id)', corpora: 'allDrives', ...ALL_DRIVES });
    if (!r.data.files?.length) throw new Error(`"${first}" (start of ${label}) is not visible to the service account. Share it (Viewer) or set POND_PHOTOS_FOLDER_ID.`);
    parent = r.data.files[0].id; corpus = { corpora: 'allDrives' };
  }
  for (const name of rest) {
    const r = await drive.files.list({ q: `'${parent}' in parents and ${FOLDER} and name='${q(name)}'`, fields: 'files(id)', ...corpus, ...ALL_DRIVES });
    if (!r.data.files?.length) throw new Error(`Folder "${name}" not found on the path ${label}. Check the names or set POND_PHOTOS_FOLDER_ID.`);
    if (r.data.files.length > 1) console.warn(`${r.data.files.length} folders named "${name}" on the path; using the first. Set POND_PHOTOS_FOLDER_ID to be exact.`);
    parent = r.data.files[0].id;
  }
  return parent;
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
