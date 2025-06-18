<!-- src/components/StatusLog.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { listenForUpdates } from '../lib/api';

  export let currentVideoId: string;

  let statusHistory: any[] = [];
  let es: EventSource | null = null;
  let errorState = false;

  onMount(() => {
    if (!currentVideoId) return;
    
    statusHistory = []; // Clear previous history
    errorState = false;

    es = listenForUpdates(
      currentVideoId,
      (data) => {
        statusHistory = [...statusHistory, data];
        // Auto-scroll logic can be added here if needed
      },
      () => {
        errorState = true;
      }
    );

    return () => {
      if (es) {
        es.close();
      }
    };
  });

  // When the video ID changes, re-establish the connection
  $: if (currentVideoId && es) {
    es.close();
    onMount(); // Rerun mount logic
  }

  onDestroy(() => {
    if (es) {
      es.close();
    }
  });
</script>  

<div class="status-log-container">
  <h4>Processing Log for {currentVideoId}</h4>
  {#if errorState}
    <p class="error">Connection to server lost. Please refresh.</p>
  {:else if statusHistory.length === 0}
    <p>Waiting for processing to start...</p>
  {:else}
    <ul>
      {#each statusHistory as status}
        <li>
          <strong>{new Date(status.timestamp).toLocaleTimeString()}:</strong>
          Stage <em>{status.stage}</em> updated to <strong>{status.status}</strong>
          - {status.message}
        </li>
      {/each}
    </ul>
  {/if}
</div>
