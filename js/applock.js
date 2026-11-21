import { extensionCall, onExtensionEvent } from './despia-extension.js';

export const appLock = (route, params = {}) => extensionCall('applock', route, params);
export const onAppLockEvent = (name, listener) => onExtensionEvent(`onAppLock${name[0].toUpperCase()}${name.slice(1)}`, listener);
