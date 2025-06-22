<!-- src/components/WorkflowManager.svelte -->
<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import Workflow from './Workflow.svelte';

  export let video: any; // The full video object from Firestore/API

  const dispatch = createEventDispatcher();

  onMount(() => {
    console.log('[WorkflowManager] Component Mounted. Initial video data:', JSON.parse(JSON.stringify(video)));
  });

  // The single source of truth for all workflow stages
  const ALL_STAGES = [
    { name: 'ingestion', description: 'Starting the process, getting video details.', longDescription: '' },
    { name: 'transcription', description: 'Converting audio to text.', longDescription: '' },
    { name: 'analysis', description: 'Analyzing the transcript for key topics and content.', longDescription: '' },
    { name: 'copywriting', description: 'Generating marketing copy and social media posts.', longDescription: '' },
    { name: 'visuals', description: 'Creating relevant images and thumbnails.', longDescription: '' },
    { name: 'publishing', description: 'Publishing content to configured platforms.', longDescription: '' },
  ];

  // A map to determine the order of stages.
  const stageOrder = new Map(ALL_STAGES.map((stage, i) => [stage.name, i]));

  // Reactive block that recalculates the stages whenever the video data changes.
  $: derivedStages = ALL_STAGES.map(stage => {
    const currentStatusString = video?.status || 'unknown';
    // Gracefully handle unknown statuses by defaulting to a very high index
    const orderOfCurrentStage = stageOrder.get(currentStatusString.replace(/_rerun$|_failed$|_complete$|^generating_|^pending_/, '')) ?? 99;
    const orderOfThisStage = stageOrder.get(stage.name) ?? 100;

    let status: 'pending' | 'active' | 'completed' | 'failed' = 'pending';

    if (currentStatusString.endsWith('_failed')) {
      if (orderOfThisStage === orderOfCurrentStage) {
        status = 'failed';
      } else if (orderOfThisStage < orderOfCurrentStage) {
        status = 'completed';
      }
    } else {
      if (orderOfThisStage < orderOfCurrentStage) {
        status = 'completed';
      } else if (orderOfThisStage === orderOfCurrentStage) {
        status = 'active';
      }
    }
    
    // Final override for the 'published' state
    if (currentStatusString === 'published' || currentStatusString === 'complete' || video?.status === 'published') {
        status = 'completed';
    }

    return {
      ...stage,
      status: status,
    };
  });

  $: if (derivedStages) {
    console.log('[WorkflowManager] Derived stages:', JSON.parse(JSON.stringify(derivedStages)));
  }

  function handleRetrigger(event: any) {
    // Forward the event up to the parent component (e.g., VideoDetail.svelte)
    dispatch('retrigger', event.detail);
  }
</script>

{#if derivedStages}
  <Workflow stages={derivedStages} on:retrigger={handleRetrigger} />
{/if} 