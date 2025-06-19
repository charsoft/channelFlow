<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Swal from 'sweetalert2';
  import { get } from 'svelte/store';
  import { accessToken } from '../lib/auth';
  import { checkVideo, sendIngest } from '../lib/api';

  const dispatch = createEventDispatcher();
  let youtubeUrl = '';
  let busy = false;

  async function submit() {
    busy = true;
    try {
      // 1) Basic guards
      if (!youtubeUrl.trim()) throw new Error('Please enter a YouTube URL.');
      const token = get(accessToken);
      if (!token) throw new Error('You must be signed in to submit a video.');

      // 2) Check if we've seen this video before
      const { exists, video_id } = await checkVideo(youtubeUrl);

      if (exists && video_id) {
        const result = await Swal.fire({
          title: 'Video Exists',
          text: "This video has been processed before. What would you like to do?",
          icon: 'question',
          showDenyButton: true,
          showCancelButton: true,
          confirmButtonText: 'Restart from Scratch',
          denyButtonText: 'Resume / View Progress',
          cancelButtonText: 'Cancel'
        });

        if (result.isConfirmed) {
          // Fall through to reprocess from scratch
        } else if (result.isDenied) {
          // Dispatch to view the video detail/resume page
          dispatch('view', { videoId: video_id });
          return;
        } else {
          // User clicked Cancel or closed the dialog
          return;
        }
      }

      // 3) Either a brand-new video, or user chose "Restart from Scratch"
      const newId = await sendIngest(youtubeUrl, true);
      dispatch('new-ingestion', { videoId: newId });
    }
    catch (err: any) {
      if (err.code === 'AUTH_REQUIRED') {
         Swal.fire({
          title: 'YouTube Account Not Connected',
          text: "You are logged in, but you haven't connected your YouTube account yet. Please connect it to proceed.",
          icon: 'warning',
          confirmButtonText: 'OK'
        });
      } else {
        Swal.fire('Error', err.message, 'error');
      }
    }
    finally {
      busy = false;
    }
  }
</script>

<form on:submit|preventDefault={submit} class="ingest-form">
  <input
    type="url"
    bind:value={youtubeUrl}
    placeholder="https://www.youtube.com/watch?v=..."
    class="url-input"
    disabled={busy}
    required
  />
  <button type="submit" disabled={busy} class="ingest-button">
    {#if busy}Processing…{:else}Amplify{/if}
  </button>
</form>

<style>
  .ingest-form {
    display: flex;
    gap: 0.5rem; /* 8px */
    width: 100%;
  }

  .url-input {
    flex-grow: 1;
    min-width: 0; /* Important for flexbox to allow shrinking */
  }

  .ingest-button {
    flex-shrink: 0; /* Prevent the button from shrinking */
  }
</style>
