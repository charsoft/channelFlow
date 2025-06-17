import { writable } from 'svelte/store';

// Create a writable store for the access token.
// We initialize it from localStorage to persist login state across page reloads.
export const accessToken = writable<string | null>(
    typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null
);

// Function to save the token to the store and localStorage.
export function setAccessToken(token: string) {
    localStorage.setItem('accessToken', token);
    accessToken.set(token);
}

// Function to clear the token on logout.
export function clearAccessToken() {
    localStorage.removeItem('accessToken');
    accessToken.set(null);
}

// Subscribe to changes in the store and update localStorage accordingly.
// This is useful if the store is updated from somewhere else.
accessToken.subscribe(value => {
    if (typeof window !== 'undefined') {
        if (value) {
            localStorage.setItem('accessToken', value);
        } else {
            localStorage.removeItem('accessToken');
        }
    }
}); 