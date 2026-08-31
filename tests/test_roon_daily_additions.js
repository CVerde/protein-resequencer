"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const test = require("node:test");

const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "roon-additions-test-"));
process.env.ROON_DAILY_ADDITIONS_STATE = path.join(temporary, "state.json");
const additions = require("../scripts/roon_daily_additions.js");

const album = (title, artist, image = null) => ({
  title, artist, image_key: image, year: null,
});

test("first library scan establishes a baseline without additions", () => {
  const state = additions.emptyState();
  const detected = additions.updateLibrary(state, [album("Debut", "Björk", "cover")],
    new Date("2026-09-01T08:00:00Z"));
  assert.deepStrictEqual(detected, []);
  assert.strictEqual(state.initialized, true);
  assert.strictEqual(Object.keys(state.known).length, 1);
});

test("later scan records only newly appearing albums", () => {
  const state = additions.emptyState();
  additions.updateLibrary(state, [album("Debut", "Björk", "one")],
    new Date("2026-09-01T08:00:00Z"));
  const detected = additions.updateLibrary(state, [
    album("Debut", "Björk", "one"), album("Homogenic", "Björk", "two"),
  ], new Date("2026-09-01T10:00:00Z"));
  assert.strictEqual(detected.length, 1);
  assert.strictEqual(detected[0].title, "Homogenic");
  assert.strictEqual(detected[0].detectedDate, "2026-09-01");
});

test("yesterday becomes printable at 00:10 Paris and only once", () => {
  const state = additions.emptyState();
  state.additions = [{ detectedDate: "2026-09-01" }];
  assert.deepStrictEqual(additions.datesDue(state,
    new Date("2026-09-01T22:09:00Z")), []);
  assert.deepStrictEqual(additions.datesDue(state,
    new Date("2026-09-01T22:10:00Z")), ["2026-09-01"]);
  state.printedDates.push("2026-09-01");
  assert.deepStrictEqual(additions.datesDue(state,
    new Date("2026-09-01T22:11:00Z")), []);
});
