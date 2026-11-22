# App Lock for Despia V3

Source preview for Despia V3. The runtime update and automatic discovery rollout are awaiting release. Rebuild and install the native app to include these files; uploading them does not change an installed app.

A ready-made extension for focus, prayer and screen-time apps. Store named groups, select apps and websites, activate several groups at once, and schedule blocks with one JavaScript API.

This experimental extension is for the Despia V3 runtime. It requires the runtime update and automatic discovery rollout currently awaiting release, plus a native rebuild. First-party V4 support comes through the new package registry. This repository does not promise a V4 port.

## Platform behavior

| Capability | iOS | Android |
| --- | --- | --- |
| App selection | Apple's native Family Activity picker | Native picker for visible launcher apps, or explicit package names |
| Categories | Apple's opaque category selections | Android ApplicationInfo category IDs, where the app supplies one, Android 8+ |
| Blocking apps | System Screen Time shields | Revocable foreground screen from a user-enabled Accessibility service |
| Websites | Screen Time domain selections and explicit domain filter | Local UDP DNS filter using a user-consented VPN slot |
| Schedules | Device Activity monitor runs without the web page | Accessibility service checks local-time windows at minute boundaries; DNS checks each query |
| Usage thresholds | Selected activity threshold through Device Activity | Not provided by this extension |

Android shields require the selected package to be visible through the launcher query or an additional query declared by the developer in the module manifest. Unknown packages fail open. System permission and role management packages are excluded through public PackageManager permission checks.

Android foreground shields do not suspend packages or block their background work, audio or notifications. The user can disable the service. Settings, the launcher, permission screens, this app, the dialer and System UI remain reachable. The shield also has a Stop all blocking button.

The Android DNS filter covers queries sent to its local UDP resolver. It does not block HTTPS paths, hard-coded IP addresses, cached DNS, DNS over HTTPS, DNS over TLS or DNS over TCP used by another app. It can replace an existing VPN only through Android's normal consent flow. It does not route other app traffic and does not support always-on lockdown. Allowed queries go over TLS to the configured upstream. The default is Google Public DNS, `8.8.8.8`, with TLS name `dns.google` on port 853.

Android API 37 emulator checks covered named groups, DNS blocking, and VPN teardown when blocking stops. Android Accessibility shielding and iOS Screen Time shielding still need device testing.

## Install

1. Copy this repository's extension files into `public/despia/applock/`. Keep `manifest.json`, `ios/` and `android/` together.
2. Add the extension name to `public/despia/extensions.json`:

   ```json
   { "extensions": ["applock"] }
   ```

3. Rebuild and install the native app with this extension. Adding files to a deployed website does not add native code to an existing binary.
4. Install the JavaScript SDK with `npm install despia-native` and import `despia` in your app's client code.

Signed build verification binds source hashes, dependency pins, app identity and final artifacts. It is separate from human code review and does not require a per-app enrollment switch.

On iOS, the Apple Developer Account Holder must obtain Family Controls distribution approval for the app and all three generated extension bundle IDs: `<your bundle id>.NXLockMonitor`, `<your bundle id>.NXLockShield` and `<your bundle id>.NXLockAction`. Provision the generated `applock` App Group for all four bundles. The manifest requests these capabilities; it cannot grant signing rights. The extension targets iOS 16.6 and later.

On Android, the module declares its own service permissions and manifest entries. An app using Accessibility for self-control needs Google Play disclosure, affirmative consent and the applicable Play declarations. Do not mark it as an accessibility tool. VPN foreground service eligibility and the Play listing also need review. This repository does not claim store approval.

See the [V3 extension guide](https://setup.despia.com/experiments/v3-extensions) and [extension skill](https://github.com/despia-legacy/extension-skill).

## JavaScript SDK

Install the published SDK in your web app:

```sh
npm install despia-native
```

Import `despia` directly from `despia-native`. The examples use SDK 1.0.28. Run native calls from browser event handlers or mounted client hooks; importing the SDK during server rendering is safe. The installed Despia V3 app must include the compiled extension.

Pass the route's exact output variable as the second argument. The SDK resolves an object whose matching property contains the full native envelope: `ok`, `code`, `error` and `data`, with runtime metadata. A native `ok: false` answer does not reject the SDK promise. Check `ok` before reading `data`. A single watched value becomes `undefined` after 30 seconds without an answer. Await calls using the same output variable sequentially.

Create a group and request authorization from a user action:

```js
import despia from 'despia-native';

const definition = {
  id: 'prayer',
  name: 'Prayer time',
  domains: [],
  android: { packages: ['com.example.game'], categories: [] },
  shield: { title: 'Prayer time', message: 'Return after your prayer.' }
};
const savedReply = await despia(
  `extension://applock/group_save?data=${encodeURIComponent(JSON.stringify(definition))}`,
  ['appLockGroupSave']
);
const saved = savedReply.appLockGroupSave;
if (!saved?.ok) throw new Error(saved?.error ?? 'No native answer');
const groupId = saved.data.group.id;

const authorizationReply = await despia(
  'extension://applock/authorization?request=true', ['appLockAuthorization']
);
const authorization = authorizationReply.appLockAuthorization;
if (!authorization?.ok) throw new Error(authorization?.error ?? 'No native answer');
```

After authorization is approved, open the native picker from a separate user action:

```js
const selectionReply = await despia(
  `extension://applock/select?id=${encodeURIComponent(groupId)}`,
  ['appLockSelect']
);
const selection = selectionReply.appLockSelect;
if (!selection?.ok) throw new Error(selection?.error ?? 'No native answer');
```

`select` returns `pending` immediately. Its native `onAppLockSelection` callback reports Save or Cancel. Query `group_get` after saving to read the stored selection counts. Then activate the group from another user action:

```js
const appliedReply = await despia(
  `extension://applock/apply?id=${encodeURIComponent(groupId)}`,
  ['appLockApply']
);
const applied = appliedReply.appLockApply;
if (!applied?.ok) throw new Error(applied?.error ?? 'No native answer');

const storedReply = await despia('extension://applock/groups', ['appLockGroups']);
const stored = storedReply.appLockGroups;
if (!stored?.ok) throw new Error(stored?.error ?? 'No native answer');
console.log(stored.data.groups);
```

Release this manual activation with `extension://applock/release?id=...`, watching `appLockRelease` and checking its envelope.

For a group with Android domains, request the DNS VPN separately before `apply`:

```js
const upstream = {
  upstream_ip: '8.8.8.8',
  upstream_tls_name: 'dns.google',
  upstream_port: 853
};
const startedReply = await despia(
  `extension://applock/android_vpn?action=start&data=${encodeURIComponent(JSON.stringify(upstream))}`,
  ['appLockAndroidVpn']
);
const started = startedReply.appLockAndroidVpn;
if (!started?.ok) throw new Error(started?.error ?? 'No native answer');
```

The disclosure and system consent are asynchronous. After the user returns, call `extension://applock/android_vpn?action=status` with `['appLockAndroidVpn']` and inspect its envelope before reading the state.

Stop the service before changing its upstream. Use a numeric IPv4 address, a real TLS certificate hostname and a port. Certificate and hostname verification remain enabled. No browsing or DNS query history is logged by the VPN. Counters and generic failures are readable through `android_vpn`.

## Groups and schedules

Group IDs belong to the app and contain 1 to 128 Unicode code points. `group_save` creates or replaces the named fields while preserving native selections when omitted. It requires `name`; omit `id` to generate one. `domains` contains DNS hostnames, without schemes, paths, ports or wildcards. International names use punycode. `shield` accepts `title`, `message`, `button`, `secondary_button`, `symbol`, `background_color`, `text_color` and `accent_color`. Colors use `#RRGGBB` on iOS. Android uses title, message, button labels and background/text colors.

Apple limits the effective explicit website filter to 50 domains across active groups. Applying a union above that limit returns `platform_limit`; a later scheduled transition records `enforcement_failed` and preserves the previous configuration. Any explicit website filtering also disables Safari private browsing, as [Apple documents](https://developer.apple.com/documentation/managedsettings/webcontentsettings/blockedbyfilter-swift.property). This is separate from the opaque website tokens chosen in the native picker.

iOS app/category/domain selections stay in native App Group storage. JavaScript receives token counts, not app bundle identifiers or individual names. Counts describe selection tokens; a category token is not an app count. Android groups hold `android.packages` and `android.categories` arrays. Read Android categories from `android_apps`; the platform can report an app as uncategorized.

```js
const schedule = {
  id: 'morning',
  group_id: 'prayer',
  start_hour: 6,
  start_minute: 0,
  end_hour: 7,
  end_minute: 0,
  weekdays: [1, 2, 3, 4, 5, 6, 7],
  time_zone: 'Asia/Dubai',
  enabled: true
};
const scheduledReply = await despia(
  `extension://applock/schedule_save?data=${encodeURIComponent(JSON.stringify(schedule))}`,
  ['appLockScheduleSave']
);
const scheduled = scheduledReply.appLockScheduleSave;
if (!scheduled?.ok) throw new Error(scheduled?.error ?? 'No native answer');
```

Weekdays use Sunday 1 through Saturday 7. End time is exclusive. A time before the start crosses midnight; selected weekdays refer to the start day. Time zones use IANA names. The schedule follows local wall-clock time, including daylight-saving changes. iOS Device Activity applies its own scheduling constraints and can reject an interval or the number of monitors. Its errors are returned; they are not reported as successful schedules.

On iOS, add `threshold_minutes` to activate the group only after the selected activity reaches that threshold inside the window. `includes_past_activity: true` requires iOS 17.4 or later. The threshold uses the group's native selection. Android returns a platform-limit error for this option.

Manual activation and schedules form a union. Releasing a manually active group does not disable its schedules. Deleting or disabling a schedule removes only that schedule. `release_all` disables every group and schedule owned by this extension and stops its Android DNS service. It does not change other apps' controls.

## Routes and responses

Read the successful payload from the envelope's `data` property. On failure, `code` identifies the native error and `error` contains its message. Each JSON `data` parameter is limited to 4096 characters by the current V3 manifest contract.

| Route | Parameters | Response | SDK output variable |
| --- | --- | --- | --- |
| `capabilities` | None | Provider and platform capability flags | `appLockCapabilities` |
| `authorization` | Optional `request`, `revoke`, iOS `member: individual` or `child` | Current authorization and pending state | `appLockAuthorization` |
| `groups` | None | `groups` array | `appLockGroups` |
| `group_get` | `id` | `group` | `appLockGroupGet` |
| `group_save` | JSON `data` | Stored `group` | `appLockGroupSave` |
| `group_delete` | `id` | `id`, `deleted` | `appLockGroupDelete` |
| `select` | `id` | `group_id`, `pending`, then `selection` event | `appLockSelect` |
| `apply`, `release` | `id` | `group_id`, `manual_enabled`, effective `active` | `appLockApply`, `appLockRelease` |
| `release_all` | None | `released` | `appLockReleaseAll` |
| `schedules` | None | Stored `schedules` | `appLockSchedules` |
| `schedule_save` | JSON `data` | Stored `schedule` | `appLockScheduleSave` |
| `schedule_delete` | `id` | `id`, `deleted` | `appLockScheduleDelete` |
| `events` | Optional `clear` | Persisted `events`, optionally removes returned entries | `appLockEvents` |
| `android_apps` | None | Visible launcher `apps`, with package, label and category | `appLockAndroidApps` |
| `android_accessibility` | Optional `request` | Accessibility/VPN authorization state | `appLockAndroidAccessibility` |
| `android_vpn` | `action: status`, `start` or `stop`; optional JSON upstream `data` | Running/pending state, counters and config | `appLockAndroidVpn` |

`authorization`, `selection` and `changed` events call `globalThis.onAppLockAuthorization`, `globalThis.onAppLockSelection` and `globalThis.onAppLockChanged`, respectively, with their payloads. The authorization callback also receives route reply envelopes containing `ok`; authorization events carry fields such as `status` and `pending`. Use the watched route variable for request answers. Assigning a function on `despia` does not register a native callback.

Register an optional selection handler in mounted client code before opening the picker:

```js
const previousAppLockHandler = globalThis.onAppLockSelection;
const handleAppLockEvent = payload => {
  if (typeof previousAppLockHandler === 'function') previousAppLockHandler(payload);
  console.log(payload);
};
globalThis.onAppLockSelection = handleAppLockEvent;

export function cleanupAppLockEvents() {
  if (globalThis.onAppLockSelection === handleAppLockEvent) {
    globalThis.onAppLockSelection = previousAppLockHandler;
  }
}
```

Call `cleanupAppLockEvents` when the client component unmounts. It restores the previous callback only while this component still owns the callback.

Native events are not replayed after reload. Read persisted state and `events` after reopening the app. `revoke` releases this extension's controls; on Android the user must disable Accessibility through the system screen. Apple authorization revocation invalidates the native selections.

## License

[Despia V3 Extension Source-Available Commercial License](LICENSE), version 1.4.
This template is proprietary and source available.

You may inspect, fork, customize, build and run it for noncommercial development,
evaluation and testing without a paid Despia license, including work on an app
you plan to release commercially later.

Production or commercial use requires a valid Despia project and an applicable
Despia license for that application and operating system. A Solo Pack covers
its licensed OS, iOS or Android. A Hybrid Pack covers both. Your applicable
license includes all provided V3 templates you have lawful access to and any
number of your own extensions, with no separate extension purchase or
per-extension fee.

Keep the license and applicable notices. Third-party material keeps its own
terms. Experimental V3 extensions do not include a commitment to maintenance
or a V4 port. See [LICENSE](LICENSE) for the full terms and [Despia](https://despia.com)
for licensing.
