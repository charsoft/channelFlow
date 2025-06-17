<!-- src/components/PreviousVideos.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import Swal from 'sweetalert2';

  interface Video {
    video_id: string;
    title?: string;
    status?: string;
    last_updated?: { _seconds: number; _nanoseconds: number } | string;
  }

  let previousVideos: Video[] = [];

  onMount(async () => {
    try {
      const res = await fetch('/api/videos');
      if (!res.ok) throw new Error('Failed to fetch video list');
      previousVideos = await res.json();
    } catch (err: any) {
      console.error(err);
      Swal.fire('Error', 'Could not load previous videos', 'error');
    }
  });

  function formatTimestamp(ts: Video['last_updated']): string {
    if (typeof ts === 'string') return new Date(ts).toLocaleString();
    if (ts && typeof ts._seconds === 'number') {
      return new Date(ts._seconds * 1000).toLocaleString();
    }
    return '—';
  }
</script>

<section class="previous-videos-section p-4 bg-white rounded-lg shadow-sm mt-6">
  <h3 class="text-lg font-semibold mb-3">Previously Processed Videos</h3>

  {#if previousVideos.length === 0}
    <p class="text-gray-500">No videos processed yet.</p>
  {:else}
    <ul class="space-y-4">
      {#each previousVideos as video}
        <li class="p-3 border border-gray-200 rounded hover:shadow">
          <a
            href={`/video/${video.video_id}`}
            class="text-indigo-600 font-medium hover:underline"
          >
            {video.title || 'Untitled video'}
          </a>
          <p><strong>ID:</strong> {video.video_id}</p>
          <p>
            <strong>Status:</strong>
            <span class="px-2 py-0.5 rounded bg-gray-100 text-sm">
              {video.status ?? 'Unknown'}
            </span>
          </p>
          <p><strong>Last Updated:</strong> {formatTimestamp(video.last_updated)}</p>
        </li>
      {/each}
    </ul>
  {/if}
</section>
