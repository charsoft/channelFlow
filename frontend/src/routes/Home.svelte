<script lang="ts">
  import IngestForm from '../components/IngestForm.svelte';
  import StatusLog from '../components/StatusLog.svelte';
  import Workflow from '../components/Workflow.svelte';
  import ConnectYouTubeButton from '../components/ConnectYouTubeButton.svelte';
  import { accessToken } from '../lib/auth';
  import { videoStatus } from '../lib/stores';
  import { listenForUpdates, checkYouTubeConnection, disconnectYouTube } from '../lib/api';
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Swal from 'sweetalert2';

  let isYouTubeConnected = false;

  onMount(async () => {
    if ($accessToken) {
      isYouTubeConnected = await checkYouTubeConnection();
    }
  });

  $: if ($accessToken) {
    checkYouTubeConnection().then(status => isYouTubeConnected = status);
  } else {
    isYouTubeConnected = false;
  }
  
  function handleNewIngestion(e: CustomEvent) {
    const videoId = e.detail.videoId;
    if (videoId) {
      listenForUpdates(videoId);
    }
  }

  function handleView(e: CustomEvent) {
    push(`/video/${e.detail.videoId}`);
  }

  function onYouTubeConnected() {
    isYouTubeConnected = true;
  }

  async function handleDisconnect() {
    try {
      await disconnectYouTube();
      isYouTubeConnected = false;
      Swal.fire('Success', 'Your YouTube account has been disconnected.', 'success');
    } catch (err: any) {
      Swal.fire('Error', err.message, 'error');
    }
  }
</script>

<div class="content-column">
  <h1 class="mb-2">Amplify your message.</h1>
  <p class="mb-4">
    Paste a YouTube link to transform a single video into a complete,
    multi-platform marketing campaign, orchestrated by autonomous AI agents.
  </p>
<p class="mb-6">
   {#if $accessToken}
    {#if isYouTubeConnected}
      <div class="ingestion-controls">
        <div class="youtube-connected-status">
          <span class="icon">✅</span>
          <span class="status-text">YouTube Connected</span>
          <button on:click={handleDisconnect} class="disconnect-button" title="Disconnect YouTube Account">×</button>
        </div>
        <IngestForm on:new-ingestion={handleNewIngestion} on:view={handleView} />
      </div>
    {:else}
      <div class="youtube-connect-prompt">
        <p>To get started, connect your YouTube account.</p>
        <ConnectYouTubeButton on:connected={onYouTubeConnected} />
      </div>
    {/if}
  {/if}
</p>
 

  {#if $videoStatus}
    <div class="processing-section">
      <Workflow />
      <StatusLog />
    </div>
  {/if}
</div>

<style>
  .processing-section {
    margin-top: 2rem;
    border-top: 1px solid #e5e7eb; /* gray-200 */
    padding-top: 2rem;
  }
  .ingestion-controls {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    /* margin-bottom: 1rem; */
    width: 100%;
  }

  .youtube-connected-status {
    display: flex;
    align-items: center;
    padding: 0.5rem 0.5rem 0.5rem 1rem; /* Adjusted padding */
    background-color: #f0fdf4; /* green-50 */
    border: 1px solid #bbf7d0; /* green-200 */
    border-radius: 0.5rem;
    color: #166534; /* green-800 */
    font-weight: 500;
    flex-shrink: 0; /* Prevent this from shrinking */
  }

  .status-text {
    margin-right: 0.75rem;
  }

  .disconnect-button {
    background: none;
    border: none;
    color: #9ca3af; /* gray-400 */
    font-size: 1.5rem;
    line-height: 1;
    cursor: pointer;
    padding: 0 0.25rem;
    border-radius: 9999px;
  }
  .disconnect-button:hover {
    color: #111827; /* gray-900 */
    background-color: #d1d5db; /* gray-300 */
  }

  .icon {
    margin-right: 0.5rem;
  }
</style>