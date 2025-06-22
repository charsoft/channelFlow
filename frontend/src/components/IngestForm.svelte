<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import Swal from 'sweetalert2';
  import { get } from 'svelte/store';
  import { accessToken } from '../lib/auth';
  import { sendIngest } from '../lib/api';

  const dispatch = createEventDispatcher();
  let youtubeUrl = '';
  let busy = false;

  const STORAGE_KEY = 'youtubeUrl';

  // When the component mounts, try to load the URL from localStorage
  onMount(() => {
    const savedUrl = localStorage.getItem(STORAGE_KEY);
    if (savedUrl) {
      youtubeUrl = savedUrl;
    }
  });

  // When the youtubeUrl changes, save it to localStorage
  $: if (youtubeUrl) {
    localStorage.setItem(STORAGE_KEY, youtubeUrl);
  }

  async function submit() {
    busy = true;
    try {
      // 1) Basic guards
      if (!youtubeUrl.trim()) throw new Error('Please enter a YouTube URL.');
      const token = get(accessToken);
      if (!token) throw new Error('You must be signed in to submit a video.');

      // No longer need to check if the video exists. The backend handles it.
      const newId = await sendIngest(youtubeUrl, false); // force=false
      dispatch('new-ingestion', { videoId: newId });

      // Clear the URL after a successful submission
      youtubeUrl = '';
      localStorage.removeItem(STORAGE_KEY);
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
    {#if busy}Processing…{:else}Go{/if}
  </button>
</form>

<style>
  .ingest-form {
    display: flex;
    gap: 0.5rem; /* 8px */
    width: 100%;
  }

  .url-input {
    width: 100%;
    min-width: 0; /* Important for flexbox to allow shrinking */
    padding: 0.5rem;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
    

  }

  .ingest-button {
    flex-shrink: 1; /* Prevent the button from shrinking */
  }
</style>
