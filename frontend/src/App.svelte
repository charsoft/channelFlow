<script lang="ts">
  import AuthButton  from './components/AuthButton.svelte';
  import IngestForm  from './components/IngestForm.svelte';
  import StatusLog   from './components/StatusLog.svelte';
  import Workflow    from './components/Workflow.svelte';
  import PreviousVideos from './components/PreviousVideos.svelte';

  let currentVideoId: string|null = null;
  let activeAgent    = '';
  let showLog        = false;

  function handleStarted(e) {
    currentVideoId = e.detail.videoId;
    showLog = true;
  }
  function handleView(e) {
    window.location.href = `/video/${e.detail.videoId}`;
  }
</script>

<main class="p-6 space-y-6">
  <!-- Already working -->
  <AuthButton />

  <!-- STEP 2: ingest form -->
  <IngestForm
    on:started={handleStarted}
    on:view={handleView}
  />

  {#if showLog}
    <StatusLog {currentVideoId} />
  {/if}

  <Workflow {activeAgent} />

  <PreviousVideos />
</main>
