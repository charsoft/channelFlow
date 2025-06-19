<!-- src/routes/Dashboard.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import Swal from 'sweetalert2';
  import { push } from 'svelte-spa-router';

  interface Video {
    video_id: string;
    title?: string;
    status?: string;
    last_updated?: { _seconds: number; _nanoseconds: number } | string;
  }

  let videos: Video[] = [];

  onMount(async () => {
    try {
      // TODO: Use the api library
      const res = await fetch('/api/videos');
      if (!res.ok) throw new Error('Failed to fetch video list');
      videos = await res.json();
    } catch (err: any) {
      console.error(err);
      Swal.fire('Error', 'Could not load videos', 'error');
    }
  });

  function formatTimestamp(ts: Video['last_updated']): string {
    if (typeof ts === 'string') return new Date(ts).toLocaleString();
    if (ts && typeof ts._seconds === 'number') {
      return new Date(ts._seconds * 1000).toLocaleString();
    }
    return '—';
  }

  function viewVideo(videoId: string) {
    push(`/video/${videoId}`);
  }
</script>

<div class="content-column">
  <h1 class="mb-4">Content Dashboard</h1>

  {#if videos.length === 0}
    <p class="text-gray-500">No videos processed yet. Start by ingesting a new video on the home page.</p>
  {:else}
    <div class="video-list-grid">
      {#each videos as video}
        <button class="video-card" on:click={() => viewVideo(video.video_id)}>
          <div class="video-card-header">
             <h3 class="video-title">{video.title || 'Untitled video'}</h3>
             <span class="status-badge">{video.status ?? 'Unknown'}</span>
          </div>
          <p class="video-id">ID: {video.video_id}</p>
          <p class="timestamp">Last Updated: {formatTimestamp(video.last_updated)}</p>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .content-column {
    max-width: 900px;
    margin: 0 auto;
  }
  .video-list-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }
  .video-card {
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    padding: 1rem;
    cursor: pointer;
    transition: box-shadow 0.2s, border-color 0.2s;
    /* Reset button styles */
    background: none;
    width: 100%;
    text-align: left;
    font-family: inherit;
    font-size: inherit;
    color: inherit;
  }
  .video-card:hover {
    border-color: #4f46e5;
    box-shadow: 0 4px 14px 0 rgba(0, 0, 0, 0.1);
  }
  .video-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.75rem;
  }
  .video-title {
    font-weight: 600;
    color: #374151;
    margin-right: 0.5rem;
  }
  .status-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 500;
    border-radius: 0.375rem;
    background-color: #f3f4f6;
    color: #4b5563;
    white-space: nowrap;
  }
  .video-id {
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 0.25rem;
  }
  .timestamp {
    font-size: 0.875rem;
    color: #6b7280;
  }
</style> 