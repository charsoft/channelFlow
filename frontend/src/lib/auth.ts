// src/lib/auth.ts
import { writable } from 'svelte/store';
import { jwtDecode } from 'jwt-decode';

interface User {
    name: string;
    // Add other user properties here if needed
}

// Create a writable store for the access token.
// We initialize it from localStorage to persist login state across page reloads.
export const accessToken = writable<string | null>(
    typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null
);

export const user = writable<User | null>(null);

// Function to save the token to the store and localStorage.
export function setAccessToken(token: string) {
    localStorage.setItem('accessToken', token);
    accessToken.set(token);
    try {
        const decodedToken: { name: string } = jwtDecode(token);
        user.set({ name: decodedToken.name });
    } catch (error) {
        console.error("Failed to decode token:", error);
        user.set(null);
    }
}

// Function to clear the token on logout.
export function clearAccessToken() {
    localStorage.removeItem('accessToken');
    accessToken.set(null);
    user.set(null);
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

// Initialize user store on load if token exists
if (typeof window !== 'undefined') {
    const token = localStorage.getItem('accessToken');
    if (token) {
        try {
            const decodedToken: { name: string } = jwtDecode(token);
            user.set({ name: decodedToken.name });
        } catch (error) {
            console.error("Failed to decode token on initial load:", error);
            user.set(null);
        }
    }
}
