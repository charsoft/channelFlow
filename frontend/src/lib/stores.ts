import { writable } from 'svelte/store';

/**
 * Stores the most recent, complete status object for the active video.
 * Components can subscribe to this to get live updates.
 * The value is null if no video is being processed.
 */
export const videoStatus = writable<any>(null);
export const youtubeConnectionStatus = writable<{ isConnected: boolean; email?: string }>({
    isConnected: false
});
/**
 * Stores a running list of all status objects received for the active video.
 * Used for displaying a historical log.
 */
export const statusHistory = writable<any[]>([]);

export const user = writable<any>(null);

/**
 * Resets all stores to their initial state.
 * Called when a new ingestion starts to clear out old data.
 */
export function resetStores() {
    videoStatus.set(null);
    statusHistory.set([]);
    user.set(null);
} 