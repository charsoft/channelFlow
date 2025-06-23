// src/lib/authUtils.ts

import { accessToken } from './auth';

let tokenCheckTimeout: ReturnType<typeof setTimeout>;

/**
 * Runs a callback whenever accessToken becomes valid (non-null),
 * with a short debounce delay to avoid flickering on first load.
 */
export function watchAccessToken(callback: () => void, debounceMs = 200) {
    return accessToken.subscribe(token => {
        if (token) {
            clearTimeout(tokenCheckTimeout);
            tokenCheckTimeout = setTimeout(callback, debounceMs);
        }
    });
}
