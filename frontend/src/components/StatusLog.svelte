<!-- src/components/StatusLog.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { listenForUpdates } from '../lib/api';
  import { idToken } from '../lib/auth';
  import { get } from 'svelte/store';

  export let currentVideoId: string;

  // Holds each status update from the server
  let statusMessages: Array<{ stage: string; status: string; message: string }> = [];

  let eventSource: EventSource | null = null;

  // Subscribe to SSE when videoId changes
  $: if (currentVideoId) {
    // clean up any previous connection
    if (eventSource) {
      eventSource.close();
    }
    statusMessages = [];
    const token = get(idToken);
    eventSource = listenForUpdates(
      currentVideoId,
      token,
      (data) => {
        // append each incoming message
        statusMessages = [...statusMessages, data];
      },
      () => {
        // on error / disconnect
        statusMessages = [
          ...statusMessages,
          { stage: 'System', status: 'error', message: 'Connection lost.' }
        ];
        eventSource?.close();
      }
    );
  }

  onDestroy(() => {
    eventSource?.close();
  });
</script>

<section class="status-section p-4 bg-gray-50 rounded-lg shadow-sm">
  <h3 class="text-lg font-semibold mb-2">Live Status Updates</h3>
  {#if statusMessages.length === 0}
    <p class="text-sm text-gray-500">Waiting for updates…</p>
  {:else}
    <ul class="space-y-1 max-h-64 overflow-y-auto text-sm font-mono">
      {#each statusMessages as { stage, status, message }, i}
        <li>
          <span class="font-semibold">[{stage}]</span>
          <span class="text-{status === 'error' ? 'red' : 'green'}-600">{status.toUpperCase()}</span>:
          {message}
        </li>
      {/each}
    </ul>
  {/if}
</section>
