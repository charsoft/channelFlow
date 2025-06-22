<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import Swal from 'sweetalert2';
  import { get } from 'svelte/store';
  import { accessToken } from '../lib/auth';
  import { sendIngest } from '../lib/api';

  const dispatch = createEventDispatcher();
  let youtubeUrl = '';
  let busy = false;
  let forceRestart = false;

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

      // 2) Confirmation for Force Restart
      if (forceRestart) {
        const result = await Swal.fire({
          title: 'Are you sure?',
          text: "This will delete all existing data for this video. If the automated YouTube download fails, you may need to re-upload the file manually.",
          icon: 'warning',
          showCancelButton: true,
          confirmButtonColor: '#d33',
          cancelButtonColor: '#3085d6',
          confirmButtonText: 'Yes, restart from scratch!',
          cancelButtonText: 'Cancel'
        });

        if (!result.isConfirmed) {
          busy = false; // Unlock the UI
          return; // Stop if the user cancels
        }
      }

      const newId = await sendIngest(youtubeUrl, forceRestart);
      dispatch('new-ingestion', { videoId: newId });

      // Clear the URL and reset the checkbox after a successful submission
      youtubeUrl = '';
      forceRestart = false;
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
  <label class="force-restart-label">
      <input type="checkbox" bind:checked={forceRestart} />
      Force Restart
  </label>
</form>

<style>
  .ingest-form {
    display: flex;
    gap: 1rem;
    align-items: center;
    width: 100%;
  }

  .url-input {
    width: 100%;
    min-width: 0; /* Important for flexbox to allow shrinking */
    padding: 0.5rem;
    border-radius: 0.5rem;
    margin-bottom: 0;
  }

  .ingest-button {
    flex-shrink: 0; /* Prevent the button from shrinking */
  }

  .force-restart-label {
    display: flex;
    align-items: center;
    white-space: nowrap;
    font-size: 0.9rem;
    color: #4b5563;
    cursor: pointer;
  }

  .force-restart-label input {
    margin-right: 0.5rem;
  }
</style>
