# Divisas COL Mobile App

## Framework

The mobile app is a real Expo React Native app, not a WebView wrapper around the
website. It targets Expo SDK 54 so it can run in Expo Go client 54.0.6. It is
intended for iOS and Android app-store distribution.

The app still uses the public website data file as its source:

```text
https://www.divisascol.com/result.json
```

## App Sections

The bottom tabs are:

- Today: latest selected city/currency summary.
- History: previous cached snapshots, up to five days.
- Rates: city and currency browsing.
- Newsletter: opens the website newsletter.
- Info: source URL, cached day count, selected date, and last fetch.

## Cache Behavior

On launch, the app loads local snapshots, then tries to fetch `result.json`.
Successful fetches are stored by date. If a date already exists, that day is
replaced. The app keeps the latest five distinct dates.

If the app is offline:

- With saved snapshots: it shows cached data and an offline message.
- Without saved snapshots: it shows a no-internet message.

## Required Software

- Node.js 20.19.4 or newer.
- npm, included with Node.js.
- Android Studio for Android builds.
- Xcode on macOS for iOS builds.

iOS builds cannot be produced directly on Windows. Use a Mac with Xcode or a
cloud/macOS build service.

## Commands

From the repository root:

```cmd
cd mobile
```

Install dependencies:

```cmd
npm install
```

Run tests:

```cmd
npm test
```

Type-check:

```cmd
npm run typecheck
```

Start Expo:

```cmd
npm start
```

Run Android:

```cmd
npm run android
```

Run iOS on macOS:

```cmd
npm run ios
```

Run web preview:

```cmd
npm run web
```
