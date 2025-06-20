<script lang="ts">
  import { onMount } from 'svelte';
  import Workflow from '../components/Workflow.svelte';
  import { listenForUpdates } from '../lib/api';

  export let params = { id: '' };
  let videoId = '';

  onMount(() => {
    videoId = params.id;
    if (videoId) {
      listenForUpdates(videoId);
    }
  });
</script>

<div class="video-detail-container">
  <h1 class="text-2xl font-bold mb-4">Video Details for {videoId}</h1>
  <p class="mb-6">
    This page will show the generated assets and details for the video.
  </p>
  
  <div class="workflow-column">
    <h2 class="mb-4">Agentic Workflow Status</h2>
    <Workflow />
  </div>

  <!-- We can add other details like the status log, generated content, etc. here later -->
</div>

<style>
  .video-detail-container {
    padding: 2rem;
  }
  .workflow-column {
    max-width: 800px;
    margin: auto;
  }
</style> 