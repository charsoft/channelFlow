<script lang="ts">
  import { onMount } from 'svelte';
  import Workflow from '../components/Workflow.svelte';
  import { listenForUpdates, retriggerStage } from '../lib/api';

  export let params = { id: '' };
  let videoId = '';

  onMount(() => {
    videoId = params.id;
    if (videoId) {
      listenForUpdates(videoId);
    }
  });

  async function handleRetrigger(stage: string) {
    try {
      await retriggerStage(videoId, stage);
      // Optional: Add a success notification
    } catch (err) {
      // Optional: Add an error notification
    }
  }
</script>

<div class="video-detail-container">
  <h1 class="text-2xl font-bold mb-4">Video Details for {videoId}</h1>
  <p class="mb-6">
    Here you can see the live progress of the workflow and re-trigger specific stages if needed.
  </p>
  
  <div class="workflow-column">
    <h2 class="mb-4">Agentic Workflow</h2>
    <Workflow retriggerable={true} on:retrigger={(e) => handleRetrigger(e.detail.stage)} />
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