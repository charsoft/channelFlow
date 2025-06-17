// src/lib/auth.ts
import { initializeApp } from 'firebase/app';
import {
    getAuth,
    onAuthStateChanged,
    GoogleAuthProvider,
    signInWithPopup,
    signOut as fbSignOut,
    type User
} from 'firebase/auth';
import { writable } from 'svelte/store';

export const currentUser = writable<User | null>(null);
export const idToken = writable<string | null>(null);

const firebaseConfig = {
    apiKey: import.meta.env.VITE_FB_API_KEY,
    authDomain: import.meta.env.VITE_FB_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FB_PROJECT_ID
};
console.log('🔑 Firebase API Key is:', import.meta.env.VITE_FB_API_KEY);

initializeApp(firebaseConfig);
const auth = getAuth();

onAuthStateChanged(auth, async (user) => {
    currentUser.set(user);
    idToken.set(user ? await user.getIdToken() : null);
});

export async function signInWithGoogle() {
    const provider = new GoogleAuthProvider();
    return signInWithPopup(auth, provider);
}

export function signOut() {
    return fbSignOut(auth);
}
