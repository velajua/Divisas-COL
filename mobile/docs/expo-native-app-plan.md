# Expo Native App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mobile web wrapper with a real Expo React Native app that can ship to iOS and Android app stores.

**Architecture:** Build a standalone Expo app in `mobile/` with a custom bottom tab layout, typed data modules, and persistent local snapshots. The website remains in `../html`; the app fetches `https://divisascol.com/result.json` and stores the latest five daily snapshots on-device.

**Tech Stack:** Expo React Native, TypeScript, AsyncStorage, Node test runner with `tsx`.

---

### Task 1: Snapshot Cache

**Files:**
- Create: `mobile/src/data/snapshotCache.ts`
- Test: `mobile/src/data/snapshotCache.test.ts`

- [ ] Write failing tests for storing one snapshot per date, replacing same-day data, sorting newest first, and keeping five days.
- [ ] Run `npm test` and confirm the tests fail because `snapshotCache.ts` does not exist.
- [ ] Implement `upsertSnapshot`, `getSnapshotDate`, and `trimSnapshots`.
- [ ] Run `npm test` and confirm the cache tests pass.

### Task 2: Result Parser

**Files:**
- Create: `mobile/src/data/resultParser.ts`
- Test: `mobile/src/data/resultParser.test.ts`

- [ ] Write failing tests for flattening compact `countries` payloads into rate rows and computing best buy/sell summaries.
- [ ] Run `npm test` and confirm the tests fail because parser functions do not exist.
- [ ] Implement `flattenRates`, `getCities`, `getCurrencies`, and `getBestRates`.
- [ ] Run `npm test` and confirm parser tests pass.

### Task 3: Expo App Shell

**Files:**
- Replace: `mobile/package.json`
- Create: `mobile/App.tsx`
- Create: `mobile/app.json`
- Create: `mobile/tsconfig.json`
- Create: `mobile/src/AppRoot.tsx`

- [ ] Replace Capacitor dependencies with Expo/React Native dependencies.
- [ ] Create an app root with bottom tabs: Today, History, Rates, Newsletter, Info.
- [ ] Keep UI native React Native components only, not a WebView.
- [ ] Run `npm test` and `npm run typecheck`.

### Task 4: App Data Flow

**Files:**
- Create: `mobile/src/data/api.ts`
- Create: `mobile/src/storage/snapshotStorage.ts`
- Modify: `mobile/src/AppRoot.tsx`

- [ ] Fetch `https://divisascol.com/result.json` on launch and manual refresh.
- [ ] Persist snapshots in AsyncStorage under the latest five daily dates.
- [ ] If offline with cache, show cached data and an offline note.
- [ ] If offline with no cache, show a clear no-internet state.
- [ ] Run `npm test` and `npm run typecheck`.

### Task 5: Documentation

**Files:**
- Replace: `mobile/docs/mobile-app.md`

- [ ] Document Node 20+, Expo, Android Studio, and Xcode requirements.
- [ ] Document app commands: `npm install`, `npm start`, `npm run android`, `npm run ios`, `npm run web`, `npm test`.
- [ ] Document that iOS builds require macOS/Xcode.
