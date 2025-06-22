<script lang="ts">
  import Swal from 'sweetalert2';
  import { videoStatus } from '../lib/stores';
  import { accessToken } from '../lib/auth';
  import { push, link } from 'svelte-spa-router';

  
  $: youtubeUrl = $videoStatus?.video_id ? 'https://youtu.be/' + $videoStatus.video_id : '';
  
  $: videoId = $videoStatus?.video_id;
  $: thumbnailUrl = videoId ? `https://img.youtube.com/vi/${videoId}/mqdefault.jpg` : '';

  let selectedFile: File | null = null;
  let fileInput: HTMLInputElement;
  let isUploading = false;
  let isCleaning = false;

  async function handleUpload() {
    if (!youtubeUrl || !selectedFile) {
        Swal.fire('Error', 'Please provide both a YouTube URL and a video file.', 'error');
        return;
    }
    isUploading = true;

    const formData = new FormData();
    formData.append('youtube_url', youtubeUrl);
    formData.append('file', selectedFile);

    try {
      const token = $accessToken;
      if (!token) {
        throw new Error('Authentication token not found. Please log in again.');
      }

      const response = await fetch('/api/admin/upload-video', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'An unknown error occurred.');
      }

      // Stop the spinner first
      isUploading = false;

      // Awaiting the toast ensures it completes before we navigate.
      await Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'success',
        title: 'Upload successful! Processing has started.',
        showConfirmButton: false,
        timer: 2000, // Shortened timer
        timerProgressBar: true
      });

      // Navigate back to the home page to watch the progress
      push('/');

    } catch (error: any) {
      isUploading = false;
      Swal.fire('Upload Failed', error.message, 'error');
    }
  }

  async function handleCleanup() {
    isCleaning = true;
    try {
      const token = $accessToken;
      if (!token) {
        throw new Error('Authentication token not found. Please log in again.');
      }
      
      const response = await fetch('/api/admin/cleanup-orphans', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'An unknown error occurred during cleanup.');
      }

      Swal.fire('Cleanup Successful', `Cleaned up ${result.cleaned_count} orphaned documents.`, 'success');

    } catch (error: any) {
      isCleaning = false;
      Swal.fire('Cleanup Failed', error.message, 'error');
    }
  }

</script>

{#if $accessToken}
  <div class="maintenance-container">
      <h1>Maintenance Tools</h1>

      <div class="tool-section">
          <h2>Manual Video Upload</h2>
          <div class="upload-instructions">
             <em> This tool is a workaround for when the automated YouTube download fails. 
              Too many automated requests can make Google think we're a bot, so 
              this manual process is a more reliable approach for this demo. 
              <strong>Please download the video from your YouTube account, then upload it here.</strong></em>
          <p> Here's a preview... the system will then process your manually uploaded file. 🙏🤓 </p>
            </div>
          <form on:submit|preventDefault={handleUpload} class="upload-form">
              {#if thumbnailUrl}
                <div class="thumbnail-preview">
                  <img src={thumbnailUrl} alt="YouTube Video Thumbnail" />
                </div>
              {/if}
              <div class="form-group">
                  <label for="youtube-url">YouTube Video URL</label>
                  <input type="url" id="youtube-url" bind:value={youtubeUrl} placeholder="https://www.youtube.com/watch?v=..." required>
              </div>
              <div class="form-group">
                  <label for="video-file">Video File (.mp4, .mov)</label>
                  <input type="file" id="video-file" bind:this={fileInput} on:change={(e) => selectedFile = e.currentTarget.files ? e.currentTarget.files[0] : null} accept="video/mp4,video/quicktime,video/x-m4v,video/mov" required>
                  <small>The original filename does not matter; it will be renamed automatically.</small>
              </div>
              <button type="submit" class="button-primary" disabled={isUploading}>
                  {#if isUploading}
                      <div class="spinner"></div>
                      <span>Uploading...</span>
                  {:else}
                      Upload and Process
                  {/if}
              </button>
          </form>
      </div>

      <div class="tool-section">
          <h2>Orphan Cleanup</h2>
          <p>
              This tool scans for and removes orphaned Firestore documents and their corresponding Cloud Storage files.
              An orphan is a record that was created but failed early in the ingestion process, leaving it in an incomplete state.
          </p>
          <button on:click={handleCleanup} class="button-danger" disabled={isCleaning}>
               {#if isCleaning}
                  <div class="spinner"></div>
                  <span>Cleaning...</span>
              {:else}
                  Run Cleanup
              {/if}
          </button>
      </div>
  </div>
{:else}
  <div class="unauthorized-container">
    <h2>Access Denied</h2>
    <p>Please log in to access ChannelFlow.</p>
    <a href="/" use:link class="button-primary">Go to Home</a>
  </div>
{/if}

<style>
  .unauthorized-container {
    text-align: center;
    max-width: 100%;
    min-height: 90vh;
    margin: 4rem auto;
    padding: 2rem;
    background-color: var(--background-color-light);
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  }
  .unauthorized-container h2 {
    font-size: 1.75rem;
    margin-bottom: 1rem;
    color: var(--danger-color);
  }

  .maintenance-container {
    max-width: 800px;
    min-height: 90vh;
    margin: 2rem auto;
    padding: 2rem;
    background-color: var(--background-color-light);
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  }

  .tool-section {
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border-color);
  }

  .tool-section:last-child {
    border-bottom: none;
    margin-bottom: 0;
  }

  h2 {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
    font-weight: 700;
    line-height: 1.2;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-fill-color: transparent;
    display: inline-block; /* Required for gradient to wrap text correctly */
  }

  p {
    font-size: 0.95rem;
    color: var(--text-color-secondary);
    margin-bottom: 1.5rem;
    line-height: 1.6;
  }

  .upload-instructions {
    font-size: 1.05rem;
  }

  .upload-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    background-color: var(--agent-bg);
    padding: 1.5rem;
    border-radius: 8px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
  }

  .form-group label {
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: var(--text-color-primary);
  }

  .form-group small {
    margin-top: 0.5rem;
    font-size: 0.8rem;
    color: var(--text-color-secondary);
  }

  .form-group input {
    padding: 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background-color: var(--background-color);
    color: var(--text-color-primary);
    font-size: 1rem;
  }

  .form-group input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px var(--primary-color-light);
  }

  .button-primary, .button-danger {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .button-primary {
    background: var(--primary-gradient);
    color: white;
  }

  .button-primary:hover:not(:disabled) {
    filter: brightness(1.15);
    transform: translateY(-2px);
  }

  .button-danger {
    background-color: var(--danger-color);
    color: white;
  }

  .button-danger:hover:not(:disabled) {
    background-color: var(--danger-color-dark);
    transform: translateY(-2px);
  }

  button:disabled {
    background: var(--border-color);
    cursor: not-allowed;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .thumbnail-preview {
    margin-bottom: 1.5rem;
    text-align: center;
  }

  .thumbnail-preview img {
    max-width: 100%;
    border-radius: 8px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    border: 1px solid var(--border-color);
  }

</style>