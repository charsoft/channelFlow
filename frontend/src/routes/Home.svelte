<script lang="ts">
  import IngestForm from '../components/IngestForm.svelte';
  import StatusLog from '../components/StatusLog.svelte';
  import Workflow from '../components/Workflow.svelte';
  import PreviousVideos from '../components/PreviousVideos.svelte';
  import ConnectYouTubeButton from '../components/ConnectYouTubeButton.svelte';
  import { accessToken } from '../lib/auth';
  import { videoStatus } from '../lib/stores';
  import { listenForUpdates, checkYouTubeConnection } from '../lib/api';
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';

  let isYouTubeConnected = false;
  let testing = true;

  onMount(async () => {
    if ($accessToken||testing) {
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
</script>

<div class="content-column">
  <h1 class="mb-2">Amplify your message.</h1>
  <p class="mb-4">
    Paste a YouTube link to transform a single video into a complete,
    multi-platform marketing campaign, orchestrated by autonomous AI agents.
  </p>
<p class="mb-6">
   {#if $accessToken||testing}
    {#if isYouTubeConnected||testing}
      <div class="ingestion-controls">
        <div class="youtube-connected-status">
          <span class="button-success"></span> ✅
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
    <StatusLog />
  {/if}
</div>



<!-- Previously processed videos -->
{#if $accessToken}
  <PreviousVideos />
{/if}

<style>
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
    padding: 0.75rem 1rem;
    background-color: #f0fdf4; /* green-50 */
    border: 1px solid #bbf7d0; /* green-200 */
    border-radius: 0.5rem;
    color: #166534; /* green-800 */
    font-weight: 500;
    flex-shrink: 0; /* Prevent this from shrinking */
  }
  .dot-green {
    width: 0.75rem;
    height: 0.75rem;
    background-color: #22c55e; /* green-500 */
    border-radius: 9999px;
    margin-right: 0.75rem;
  }
</style>