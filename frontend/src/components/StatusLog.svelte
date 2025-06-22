<!-- src/components/StatusLog.svelte -->
<script lang="ts">
  import { statusHistory, videoStatus } from '../lib/stores';

  let dedupedHistory: any[] = [];
  $: {
    dedupedHistory = $statusHistory.filter((current, i, arr) => {
      // Always keep the very first status
      if (i === 0) return true;
      const previous = arr[i - 1];
      // Keep it if the status or the message has changed
      return current.status !== previous.status || current.status_message !== previous.status_message;
    });
  }
</script>  

<div class="status-log-container">
  <h4>Processing Log for {$videoStatus?.video_id}</h4>
  {#if dedupedHistory.length === 0}
    <p>Waiting for processing to start...</p>
  {:else}
    <ul>
      {#each dedupedHistory as status, i (i)}
        <li>
          <strong>{new Date(status.updated_at).toLocaleTimeString()}:</strong>
          Stage <em>{status.status}</em> - {status.status_message || 'Update received.'}
          {#if status.status === 'failed' && status.error}
            <span class="error-message">Error: {status.error}</span>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .error-message {
    color: #ef4444; /* red-500 */
    font-weight: bold;
    margin-left: 0.5rem;
  }
</style>
