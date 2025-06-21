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
    class="url-input"
    type="text"
    bind:value={videoUrl}
    placeholder="e.g., https://www.youtube.com/watch?v=your_video_id"
    disabled={isLoading}
  />
  <button type="submit" class="button-primary ingest-button" disabled={isLoading || !videoUrl.trim()}>
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
    align-items: center;
  }

  .url-input {
    flex-grow: 1;
    padding: 0.6rem 0.8rem;
    border: 1px solid #e2e8f0;
    border-radius: 0.375rem;
    font-size: 1rem;
    color: #374151;
  }
  .url-input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
  }

  .ingest-button {
    flex-shrink: 0; /* Prevent the button from shrinking */
  }

  .spinner {
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    width: 16px;
    height: 16px;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 8px;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
