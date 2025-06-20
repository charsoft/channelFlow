<script lang="ts">
  import { onMount } from 'svelte';
  import Swal from 'sweetalert2';
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

  async function handleRetrigger(event: { detail: { stage: string }}) {
    const stage = event.detail.stage;
    
    Swal.fire({
      title: 'Are you sure?',
      text: `This will re-run the process from the '${stage}' stage.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#3085d6',
      cancelButtonColor: '#d33',
      confirmButtonText: 'Yes, re-run it!'
    }).then(async (result) => {
      if (result.isConfirmed) {
        try {
          await retriggerStage(videoId, stage);
          Swal.fire(
            'Restarted!',
            `The process will now re-run from the ${stage} stage.`,
            'success'
          );
        } catch (err: any) {
          Swal.fire(
            'Error!',
            err.message || 'Failed to re-trigger the process.',
            'error'
          );
        }
      }
    });
  }
</script>

<div class="video-detail-container">
  <h1 class="text-2xl font-bold mb-4">Video Details for {videoId}</h1>
  <p class="mb-6">
    Here you can see the live progress of the workflow and re-trigger specific stages if needed.
  </p>
  
  <div class="workflow-column">
    <h2 class="mb-4">Agentic Workflow</h2>
    <Workflow retriggerable={true} on:retrigger={handleRetrigger} />
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