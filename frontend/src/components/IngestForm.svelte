<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Swal from 'sweetalert2';
  import { get } from 'svelte/store';
  import { accessToken } from '../lib/auth';
  import { sendIngest } from '../lib/api';

  const dispatch = createEventDispatcher();
  let videoUrl = '';
  let isLoading = false;

  async function submit() {
    isLoading = true;
    try {
      // 1) Basic guards
      if (!videoUrl.trim()) throw new Error('Please enter a YouTube URL.');
      const token = get(accessToken);
      if (!token) throw new Error('You must be signed in to submit a video.');

      // No longer need to check if the video exists. The backend handles it.
      const newId = await sendIngest(videoUrl, false); // force=false
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
      isLoading = false;
    }
  }
</script>

<form on:submit|preventDefault={submit} class="ingest-form">
  <input
    type="text"
    bind:value={videoUrl}
    placeholder="Enter YouTube Video URL"
    disabled={isLoading}
  />
  <button type="submit" class="button-primary" disabled={isLoading || !videoUrl.trim()}>
    {#if isLoading}
      <div class="spinner" />
      <span>Ingesting...</span>
    {:else}
      Ingest Video
    {/if}
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
