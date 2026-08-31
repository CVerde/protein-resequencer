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

test("records a track only once until the zone changes track", async () => {
  watcher.writeState(watcher.emptyState("2026-08-30"));
  const data = { zone_id: "zone", now_playing: {
    state: "playing", artist: "Björk", album: "Debut", title: "Human Behaviour", duration: 252,
  }};
  assert.strictEqual(await watcher.recordNowPlaying(data,
    new Date("2026-08-30T12:07:00Z")), "recorded");
  assert.strictEqual(await watcher.recordNowPlaying(data,
    new Date("2026-08-30T12:08:00Z")), "duplicate");
  const state = watcher.readState();
  assert.strictEqual(state.tracks.length, 1);
  assert.strictEqual(state.tracks[0].time, "14h07");
  assert.strictEqual("year" in state.tracks[0], false);
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
