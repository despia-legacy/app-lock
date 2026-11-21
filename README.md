# App Lock for Despia V3

Source preview for Despia V3. This snapshot requires the runtime update currently awaiting release and an approved extension-enabled native build. Uploading these files does not change an installed app.

A ready-made extension for focus, prayer and screen-time apps. Store named groups, select apps and websites, activate several groups at once, and schedule blocks with one JavaScript API.

This experimental extension is for the Despia V3 runtime. It requires the runtime update currently awaiting release and an approved extension-enabled native build. First-party V4 support comes through the new package registry. This repository does not promise a V4 port.

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

Native Screen Time shielding and Android Accessibility/VPN enforcement are not yet tested on devices.

## Install

1. Copy this repository's extension files into `public/despia/applock/`. Keep `manifest.json`, `ios/` and `android/` together.
2. Add the extension name to `public/despia/extensions.json`:

   ```json
   { "extensions": ["applock"] }
   ```

3. Rebuild with an approved Despia V3 extension build. Adding files to a deployed website does not add native code to an existing binary.
4. Install the JavaScript SDK with `npm install despia-native`. Copy `js/` into your app's client code and import its helper.

On iOS, the Apple Developer Account Holder must obtain Family Controls distribution approval for the app and all three generated extension bundle IDs: `<your bundle id>.NXLockMonitor`, `<your bundle id>.NXLockShield` and `<your bundle id>.NXLockAction`. Provision the generated `applock` App Group for all four bundles. The manifest requests these capabilities; it cannot grant signing rights. The extension targets iOS 16.6 and later.

On Android, the module declares its own service permissions and manifest entries. An app using Accessibility for self-control needs Google Play disclosure, affirmative consent and the applicable Play declarations. Do not mark it as an accessibility tool. VPN foreground service eligibility and the Play listing also need review. This repository does not claim store approval.

See the [V3 extension guide](https://setup.despia.com/experiments/v3-extensions) and [extension skill](https://github.com/despia-legacy/extension-skill).

## JavaScript SDK

Use the helper from a client event handler, React effect or Vue mounted callback. SSR code must wait until the client is mounted. The helper uses `despia-native`, adds a unique callback for each request, checks the native envelope, and cleans up its temporary callback and watched property.

```js
import { appLock, onAppLockEvent } from './lib/applock.js';

const { group } = await appLock('group_save', {
  data: {
    id: 'prayer',
    name: 'Prayer time',
    domains: [],
    android: { packages: ['com.example.game'], categories: [] },
    shield: { title: 'Prayer time', message: 'Return after your prayer.' }
  }
});

const unsubscribe = onAppLockEvent('selection', async event => {
  if (event.group_id === group.id && !event.cancelled && !event.error) {
    console.log(await appLock('group_get', { id: group.id }));
  }
});

await appLock('authorization', { request: true });
// After authorization is approved, open the native picker from a user action.
await appLock('select', { id: group.id });
// Select returns pending immediately. The selection event reports Save or Cancel.
// Activate from a separate user action after the selection is saved.
const activateGroup = () => appLock('apply', { id: group.id });

const { groups } = await appLock('groups');
await appLock('release', { id: group.id });
unsubscribe();
```

For a group with Android domains, request the DNS VPN separately before `apply`:

```js
await appLock('android_vpn', {
  action: 'start',
  data: {
    upstream_ip: '8.8.8.8',
    upstream_tls_name: 'dns.google',
    upstream_port: 853
  }
});
// The normal disclosure and system consent are asynchronous.
const status = await appLock('android_vpn', { action: 'status' });
```

Stop the service before changing its upstream. Use a numeric IPv4 address, a real TLS certificate hostname and a port. Certificate and hostname verification remain enabled. No browsing or DNS query history is logged by the VPN. Counters and generic failures are readable through `android_vpn`.

## Groups and schedules

Group IDs belong to the app and contain 1 to 128 Unicode code points. `group_save` creates or replaces the named fields while preserving native selections when omitted. It requires `name`; omit `id` to generate one. `domains` contains DNS hostnames, without schemes, paths, ports or wildcards. International names use punycode. `shield` accepts `title`, `message`, `button`, `secondary_button`, `symbol`, `background_color`, `text_color` and `accent_color`. Colors use `#RRGGBB` on iOS. Android uses title, message, button labels and background/text colors.

Apple limits the effective explicit website filter to 50 domains across active groups. Applying a union above that limit returns `platform_limit`; a later scheduled transition records `enforcement_failed` and preserves the previous configuration. Any explicit website filtering also disables Safari private browsing, as [Apple documents](https://developer.apple.com/documentation/managedsettings/webcontentsettings/blockedbyfilter-swift.property). This is separate from the opaque website tokens chosen in the native picker.

iOS app/category/domain selections stay in native App Group storage. JavaScript receives token counts, not app bundle identifiers or individual names. Counts describe selection tokens; a category token is not an app count. Android groups hold `android.packages` and `android.categories` arrays. Read Android categories from `android_apps`; the platform can report an app as uncategorized.

```js
await appLock('schedule_save', {
  data: {
    id: 'morning',
    group_id: 'prayer',
    start_hour: 6,
    start_minute: 0,
    end_hour: 7,
    end_minute: 0,
    weekdays: [1, 2, 3, 4, 5, 6, 7],
    time_zone: 'Asia/Dubai',
    enabled: true
  }
});
```

Weekdays use Sunday 1 through Saturday 7. End time is exclusive. A time before the start crosses midnight; selected weekdays refer to the start day. Time zones use IANA names. The schedule follows local wall-clock time, including daylight-saving changes. iOS Device Activity applies its own scheduling constraints and can reject an interval or the number of monitors. Its errors are returned; they are not reported as successful schedules.

On iOS, add `threshold_minutes` to activate the group only after the selected activity reaches that threshold inside the window. `includes_past_activity: true` requires iOS 17.4 or later. The threshold uses the group's native selection. Android returns a platform-limit error for this option.

Manual activation and schedules form a union. Releasing a manually active group does not disable its schedules. Deleting or disabling a schedule removes only that schedule. `release_all` disables every group and schedule owned by this extension and stops its Android DNS service. It does not change other apps' controls.

## Routes and responses

The SDK helper returns the native `data` object or throws with the native error code. A missing response has `sdk_timeout`. Each JSON `data` parameter is limited to 4096 characters by the current V3 manifest contract.

| Route | Parameters | Response |
| --- | --- | --- |
| `capabilities` | None | Provider and platform capability flags |
| `authorization` | Optional `request`, `revoke`, iOS `member: individual` or `child` | Current authorization and pending state |
| `groups` | None | `groups` array |
| `group_get` | `id` | `group` |
| `group_save` | JSON `data` | Stored `group` |
| `group_delete` | `id` | `id`, `deleted` |
| `select` | `id` | `group_id`, `pending`, then `selection` event |
| `apply`, `release` | `id` | `group_id`, `manual_enabled`, effective `active` |
| `release_all` | None | `released` |
| `schedules` | None | Stored `schedules` |
| `schedule_save` | JSON `data` | Stored `schedule` |
| `schedule_delete` | `id` | `id`, `deleted` |
| `events` | Optional `clear` | Persisted `events`, optionally removes returned entries |
| `android_apps` | None | Visible launcher `apps`, with package, label and category |
| `android_accessibility` | Optional `request` | Accessibility/VPN authorization state |
| `android_vpn` | `action: status`, `start` or `stop`; optional JSON upstream `data` | Running/pending state, counters and config |

`authorization`, `selection` and `changed` events notify a loaded document through `onAppLockEvent`. They are not replayed after reload. Read persisted state and `events` after reopening the app. `revoke` releases this extension's controls; on Android the user must disable Accessibility through the system screen. Apple authorization revocation invalidates the native selections.

## License

Source available under the [Despia Extension License](LICENSE). Use requires a valid Despia commercial license and Despia project for each application and operating system. This is not an open-source license.

## Source and licensing

Browse, clone or fork this source to inspect it. Public GitHub forks remain public. For private development, clone into a private workspace or private repository. Modification, building, execution and deployment require a valid Despia commercial license and a valid Despia project for the application. The standard price is USD 249 per application per operating system. Licensed users may customize the extension or use it as a reference for new functionality in that licensed app. Keep the license and applicable notices. See [LICENSE](LICENSE) for the terms.
