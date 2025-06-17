<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Swal from 'sweetalert2';
  import { get } from 'svelte/store';
  import { idToken } from '../lib/auth';
  import { checkVideo, sendIngest } from '../lib/api';

  const dispatch = createEventDispatcher();
  let youtubeUrl = '';
  let busy = false;

  async function submit() {
    busy = true;
    try {
      // 1) Basic guards
      if (!youtubeUrl.trim()) throw new Error('Please enter a YouTube URL.');
      const token = get(idToken);
      if (!token) throw new Error('You must be signed in.');

      // 2) Check if we’ve seen this video before
      const { exists, video_id } = await checkVideo(youtubeUrl, token);

      if (exists && video_id) {
        // Prompt user: reprocess or just view
        const res = await Swal.fire({
          title: 'Video Already Processed',
          text: 'Would you like to reprocess it or view existing results?',
          icon: 'question',
          showDenyButton: true,
          confirmButtonText: 'Reprocess',
          denyButtonText: 'View Existing'
        });

        if (res.isDenied) {
          dispatch('view', { videoId: video_id });
          return;
        }
        // else fall through to reprocess
      }

      // 3) Either brand-new video, or user chose Reprocess
      const newId = await sendIngest(youtubeUrl, true, token);
      dispatch('started', { videoId: newId });
    }
    catch (err: any) {
      // Special case: backend says AUTH_REQUIRED
      if (err.code === 'AUTH_REQUIRED') {
        const choice = await Swal.fire({
          title: 'YouTube Auth Needed',
          text: err.message,
          icon: 'warning',
          showCancelButton: true,
          confirmButtonText: 'Connect YouTube'
        });
        if (choice.isConfirmed) {
          dispatch('requireYouTube');
        }
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
