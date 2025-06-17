// src/lib/api.ts
import type { Writable } from 'svelte/store';

export async function checkVideo(
    url: string,
    token: string
): Promise<{ exists: boolean; video_id?: string }> {
    const res = await fetch('/api/ingest-url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ url, force: false })
    });
    if (res.status === 403) {
        const err = await res.json();
        return { exists: true, video_id: err.data.video_id };
    }
    const json = await res.json();
    return { exists: json.status === 'exists', video_id: json.data.video_id };
}

export async function sendIngest(
    url: string,
    force: boolean,
    token: string
): Promise<string> {
    const res = await fetch('/api/ingest-url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ url, force })
    });
    const json = await res.json();
    return json.video_id;
}

export function listenForUpdates(
    videoId: string,
    token: string,
    onMessage: (data: any) => void,
    onError: () => void
) {
    const es = new EventSource(`/api/events/${videoId}?token=${encodeURIComponent(token)}`);
    es.onmessage = e => onMessage(JSON.parse(e.data));
    es.onerror = () => { es.close(); onError(); };
    return es;
}
