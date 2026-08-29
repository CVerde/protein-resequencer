"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const test = require("node:test");

const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "roon-watcher-test-"));
process.env.ROON_ALBUM_PRINT_STATE = path.join(temporary, "state.json");
const watcher = require("../scripts/roon_album_watcher.js");

test("normalise album and artist for daily deduplication", () => {
  assert.strictEqual(
    watcher.albumKey({ artist: " Moderat ", album: "MODERAT" }),
    "moderat|moderat"
  );
});

test("formats broadcast time in Europe/Paris", () => {
  assert.strictEqual(watcher.parisTime(new Date("2026-01-15T20:05:00Z")), "21:05");
});

test("only accepts playing events with artwork and album metadata", () => {
  const base = { zone_id: "zone", now_playing: {
    state: "playing", artist: "Goodge", album: "Soul Spectrums", image_key: "image"
  }};
  assert.strictEqual(watcher.allowedEvent(base), true);
  assert.strictEqual(watcher.allowedEvent({ ...base, now_playing: { ...base.now_playing, state: "paused" }}), false);
});

test("prints an album once per day and records only after success", async () => {
  const data = { zone_id: "zone", now_playing: {
    state: "playing", artist: "Goodge", album: "Soul Spectrums", image_key: "image"
  }};
  const fakeFetch = async () => ({
    ok: true,
    headers: { get: () => "image/jpeg" },
    arrayBuffer: async () => Uint8Array.from([1, 2, 3]).buffer,
  });
  let prints = 0;
  const fakePrint = async () => { prints += 1; };
  assert.strictEqual(await watcher.handleNowPlaying(data, fakeFetch, fakePrint), "printed");
  assert.strictEqual(await watcher.handleNowPlaying(data, fakeFetch, fakePrint), "duplicate");
  assert.strictEqual(prints, 1);
});
