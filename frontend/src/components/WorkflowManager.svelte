<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Workflow from './Workflow.svelte';

  export let video: any;
  export let stagesMetadata: { name: string; description: string; longDescription: string }[] = [];

  const dispatch = createEventDispatcher();

  $: stageOrder = new Map((stagesMetadata ?? []).map((stage, i) => [stage.name.toLowerCase(), i]));

  const statusToStageMap: Record<string, string> = {
    "ingesting": "ingestion",
    "downloading": "ingestion",
    "ingested": "ingestion",
    "ingestion": "ingestion",
    "ingestion_failed": "ingestion",

    "transcribing": "transcription",
    "transcribed": "transcription",
    "transcription": "transcription",
    "transcribing_failed": "transcription",
    "transcription_failed": "transcription",
    "auth_failed": "transcription",

    "analyzing": "analysis",
    "analyzed": "analysis",
    "analysis": "analysis",
    "analyzing_failed": "analysis",
    "analysis_failed": "analysis",

    "generating_copy": "copywriting",
    "copy_generated": "copywriting",
    "copywriting": "copywriting",
    "copy": "copywriting",
    "generating_copy_failed": "copywriting",
    "copy_failed": "copywriting",

    "generating_visuals": "visuals",
    "visuals_generated": "visuals",
    "visuals": "visuals",
    "generating_visuals_failed": "visuals",
    "visuals_failed": "visuals",

    "publishing": "publishing",
    "published": "publishing",
    "publisher": "publishing",
    "publishing_failed": "publishing"
  };

  $: derivedStages = (() => {
    if (!video?.status || !stagesMetadata.length) return [];

    const currentStatus = video.status;
    const normalized = currentStatus.replace(/_rerun$|_failed$|_complete$|^generating_|^pending_/, '');
    const stageKey = statusToStageMap[normalized] || 'unknown';

    if (stageKey === 'unknown') {
      console.warn('[WorkflowManager] Unknown stage key:', normalized);
    }

    const orderOfCurrentStage = stageOrder.get(stageKey.toLowerCase()) ?? -1;

    return stagesMetadata.map(stage => {
      const orderOfThisStage = stageOrder.get(stage.name.toLowerCase()) ?? 100;
      let status: 'pending' | 'active' | 'completed' | 'failed' = 'pending';

      if (orderOfCurrentStage === -1) {
        status = 'pending';
      } else if (currentStatus.endsWith('_failed')) {
        if (orderOfThisStage === orderOfCurrentStage) status = 'failed';
        else if (orderOfThisStage < orderOfCurrentStage) status = 'completed';
      } else {
        if (orderOfThisStage < orderOfCurrentStage) status = 'completed';
        else if (orderOfThisStage === orderOfCurrentStage) status = 'active';
      }

      if (
        currentStatus === 'published' ||
        (currentStatus === 'complete' && stage.name.toLowerCase() === 'publisher')
      ) {
        status = 'completed';
      }

      console.log(`[🧪 STAGE CHECK] ${stage.name} | order: ${orderOfThisStage}, currentOrder: ${orderOfCurrentStage}, final status: ${status}`);

      return {
        ...stage,
        status,
      };
    });
  })();

  function handleRetrigger(event: any) {
    dispatch('retrigger', event.detail);
  }
</script>

<!-- <p style="color:red">DEBUG: derivedStages = {JSON.stringify(derivedStages)}</p> -->

{#if derivedStages.length}
  <Workflow stages={derivedStages} on:retrigger={handleRetrigger} />
{/if}
