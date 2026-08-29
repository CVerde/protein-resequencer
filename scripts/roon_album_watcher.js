#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const SONGR_URL = process.env.SONGR_URL || "http://127.0.0.1:3333";
const SOCKET_CLIENT_PATH = process.env.SONGR_SOCKET_IO_CLIENT ||
  "/home/pi/songr/node_modules/socket.io-client";
const STATE_FILE = process.env.ROON_ALBUM_PRINT_STATE ||
  "/home/pi/.local/state/protein-resequencer/printed-albums.json";
const PYTHON = process.env.PYTHON || "python3";
const PRINT_SCRIPT = path.join(__dirname, "print_album_art.py");
const ZONE_IDS = new Set((process.env.ROON_PRINT_ZONE_IDS || "")
  .split(",").map(value => value.trim()).filter(Boolean));
const CATALOG_CACHE_MS = 5 * 60 * 1000;
let catalogCache = null;
let catalogCachedAt = 0;

function log(message) {
  process.stdout.write(`[${new Date().toISOString()}] ${message}\n`);
}

function parisDate(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Paris", year: "numeric", month: "2-digit", day: "2-digit"
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function parisTime(now = new Date()) {
  return new Intl.DateTimeFormat("fr-FR", {
    timeZone: "Europe/Paris", hour: "2-digit", minute: "2-digit", hour12: false
  }).format(now);
}

function parisBroadcastTime(now = new Date()) {
  const parts = new Intl.DateTimeFormat("fr-FR", {
    timeZone: "Europe/Paris", day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.day}/${values.month}/${values.year} à ${values.hour}:${values.minute}`;
}

function normalizeText(value) {
  return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim().toLocaleLowerCase("fr-FR");
}

function albumKey(nowPlaying) {
  const artist = normalizeText(nowPlaying.artist);
  const album = normalizeText(nowPlaying.album);
  return artist && album ? `${artist}|${album}` : `image:${nowPlaying.image_key || ""}`;
}

function findCatalogYear(index, nowPlaying) {
  if (Number.isInteger(nowPlaying.year)) return nowPlaying.year;
  const wantedArtist = normalizeText(nowPlaying.artist);
  const wantedAlbum = normalizeText(nowPlaying.album);
  const albums = index && Array.isArray(index.albums) ? index.albums : [];
  const match = albums.find(album => normalizeText(album.artist) === wantedArtist &&
    normalizeText(album.title) === wantedAlbum);
  if (!match) return "";
  return match.originalReleaseYear || match.editionReleaseYear ||
    (match.originalReleaseDate && match.originalReleaseDate.year) ||
    (match.releaseDate && match.releaseDate.year) || "";
}

async function resolveYear(nowPlaying, fetchImpl = fetch) {
  if (Number.isInteger(nowPlaying.year)) return nowPlaying.year;
  try {
    const now = Date.now();
    if (!catalogCache || now - catalogCachedAt >= CATALOG_CACHE_MS) {
      const response = await fetchImpl(`${SONGR_URL}/api/catalog/index`, {
        signal: AbortSignal.timeout(4000),
      });
      if (!response.ok) throw new Error(`catalogue HTTP ${response.status}`);
      catalogCache = await response.json();
      catalogCachedAt = now;
    }
    return findCatalogYear(catalogCache, nowPlaying);
  } catch (error) {
    log(`Année Songr indisponible : ${error.message}`);
    return "";
  }
}

function readState(today = parisDate()) {
  try {
    const parsed = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
    if (parsed.date === today && parsed.albums && typeof parsed.albums === "object") return parsed;
  } catch (_) {}
  return { date: today, albums: {} };
}

function writeState(state) {
  fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
  const temporary = `${STATE_FILE}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, JSON.stringify(state, null, 2) + "\n", "utf8");
  fs.renameSync(temporary, STATE_FILE);
}

function allowedEvent(data) {
  const nowPlaying = data && data.now_playing;
  if (!nowPlaying || nowPlaying.state !== "playing") return false;
  if (!nowPlaying.image_key || !nowPlaying.album || !nowPlaying.artist) return false;
  if (ZONE_IDS.size && !ZONE_IDS.has(data.zone_id)) return false;
  return true;
}

function runPrinter(imagePath, nowPlaying) {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON, [PRINT_SCRIPT, imagePath,
      "--album", nowPlaying.album, "--artist", nowPlaying.artist,
      "--track", nowPlaying.title || "", "--year", String(nowPlaying.year || ""),
      "--played-at", parisBroadcastTime()], { stdio: "inherit" });
    child.once("error", reject);
    child.once("exit", code => code === 0 ? resolve() : reject(new Error(`impression terminée avec le code ${code}`)));
  });
}

async function handleNowPlaying(data, fetchImpl = fetch, printImpl = runPrinter) {
  if (!allowedEvent(data)) return "ignored";
  const nowPlaying = data.now_playing;
  const key = albumKey(nowPlaying);
  const state = readState();
  if (state.albums[key]) {
    log(`Déjà imprimé aujourd'hui : ${nowPlaying.artist} — ${nowPlaying.album}`);
    return "duplicate";
  }

  const temporaryDirectory = fs.mkdtempSync(path.join(os.tmpdir(), "roon-album-"));
  const imagePath = path.join(temporaryDirectory, "cover");
  try {
    const enrichedNowPlaying = { ...nowPlaying, year: await resolveYear(nowPlaying, fetchImpl) };
    const imageUrl = `${SONGR_URL}/api/image/${encodeURIComponent(nowPlaying.image_key)}` +
      "?scale=fit&width=384&height=384";
    const response = await fetchImpl(imageUrl);
    if (!response.ok) throw new Error(`pochette HTTP ${response.status}`);
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.startsWith("image/")) throw new Error(`type de pochette invalide : ${contentType}`);
    fs.writeFileSync(imagePath, Buffer.from(await response.arrayBuffer()));
    await printImpl(imagePath, enrichedNowPlaying);
    const freshState = readState();
    freshState.albums[key] = {
      artist: nowPlaying.artist, album: nowPlaying.album,
      year: enrichedNowPlaying.year || null, image_key: nowPlaying.image_key,
      printed_at: new Date().toISOString(), zone_id: data.zone_id
    };
    writeState(freshState);
    log(`Imprimé : ${nowPlaying.artist} — ${nowPlaying.album}`);
    return "printed";
  } finally {
    fs.rmSync(temporaryDirectory, { recursive: true, force: true });
  }
}

function main() {
  let io;
  try { ({ io } = require(SOCKET_CLIENT_PATH)); }
  catch (error) { log(`Socket.IO introuvable : ${error.message}`); process.exit(1); }
  const socket = io(SONGR_URL, { reconnection: true, reconnectionDelay: 2000 });
  let queue = Promise.resolve();
  socket.on("connect", () => log(`Connecté à Songr (${socket.id})`));
  socket.on("disconnect", reason => log(`Déconnecté de Songr : ${reason}`));
  socket.on("connect_error", error => log(`Connexion Songr impossible : ${error.message}`));
  socket.on("now-playing-updated", data => {
    queue = queue.then(() => handleNowPlaying(data)).catch(error => log(`Erreur : ${error.message}`));
  });
}

if (require.main === module) main();

module.exports = { albumKey, allowedEvent, findCatalogYear, handleNowPlaying, normalizeText,
  parisBroadcastTime, parisDate, parisTime, readState, resolveYear, writeState };
