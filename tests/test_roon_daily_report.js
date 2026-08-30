"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const test = require("node:test");

const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "roon-report-test-"));
process.env.ROON_DAILY_REPORT_STATE = path.join(temporary, "state.json");
const watcher = require("../scripts/roon_daily_report.js");

test("formats Paris date and time", () => {
  const now = new Date("2026-01-15T20:05:00Z");
  assert.strictEqual(watcher.parisDate(now), "2026-01-15");
  assert.strictEqual(watcher.parisTime(now), "21h05");
});

test("finds original year with accent-insensitive matching", () => {
  const index = { albums: [{ artist: "Björk", title: "Début",
    originalReleaseYear: 1993, editionReleaseYear: 2013 }] };
  assert.strictEqual(watcher.findCatalogYear(index, { artist: "Bjork", album: "Debut" }), 1993);
});

test("matches an album artist inside a collaborative track credit", () => {
  assert.strictEqual(watcher.artistMatches("Bo Ningen", "Bo Ningen / Bobby Gillespie"), true);
  const index = { albums: [{ artist: "Bo Ningen", title: "Sudden Fictions",
    originalReleaseYear: 2020 }] };
  assert.strictEqual(watcher.findCatalogYear(index, {
    artist: "Bo Ningen / Bobby Gillespie", album: "Sudden Fictions",
  }), 2020);
});

test("accepts only an exact high-score MusicBrainz release group", () => {
  const result = { "release-groups": [{
    score: 100, title: "A thousand doors, just one key",
    "first-release-date": "2025-02-14",
    "artist-credit": [{ name: "Feldup" }],
  }] };
  assert.strictEqual(watcher.findMusicBrainzYear(result, {
    artist: "Feldup", album: "A Thousand Doors, Just One Key",
  }), 2025);
});

test("records a track only once until the zone changes track", async () => {
  watcher.writeState(watcher.emptyState("2026-08-30"));
  const data = { zone_id: "zone", now_playing: {
    state: "playing", artist: "Björk", album: "Debut", title: "Human Behaviour", duration: 252,
  }};
  const fetchCatalog = async () => ({ ok: true, json: async () => ({ albums: [{
    artist: "Björk", title: "Debut", originalReleaseYear: 1993,
  }] }) });
  assert.strictEqual(await watcher.recordNowPlaying(data, fetchCatalog,
    new Date("2026-08-30T12:07:00Z")), "recorded");
  assert.strictEqual(await watcher.recordNowPlaying(data, fetchCatalog,
    new Date("2026-08-30T12:08:00Z")), "duplicate");
  const state = watcher.readState();
  assert.strictEqual(state.tracks.length, 1);
  assert.strictEqual(state.tracks[0].time, "14h07");
  assert.strictEqual(state.tracks[0].year, 1993);
  assert.strictEqual(state.tracks[0].duration, 252);
});

test("prints yesterday before starting a new day", async () => {
  watcher.writeState({ date: "2026-08-29", tracks: [{ title: "Titre" }], lastByZone: {} });
  let printed;
  const changed = await watcher.rolloverIfNeeded(async report => { printed = report; },
    new Date("2026-08-29T22:00:05Z"));
  assert.strictEqual(changed, true);
  assert.strictEqual(printed.date, "2026-08-29");
  assert.strictEqual(watcher.readState().date, "2026-08-30");
});

test("enriches tracks already recorded without a year", async () => {
  watcher.writeState({ date: "2026-08-30", tracks: [{
    time: "16h20", title: "Take it slow", album: "A thousand doors, just one key",
    year: null, artist: "Feldup", zoneId: "zone",
  }], lastByZone: {} });
  const fakeFetch = async url => url.includes("/api/catalog/index")
    ? { ok: true, json: async () => ({ albums: [] }) }
    : { ok: true, json: async () => ({ "release-groups": [{
      score: 100, title: "A thousand doors, just one key",
      "first-release-date": "2025-01-01", "artist-credit": [{ name: "Feldup" }],
    }] }) };
  assert.strictEqual(await watcher.enrichMissingYears(fakeFetch), true);
  assert.strictEqual(watcher.readState().tracks[0].year, 2025);
});
