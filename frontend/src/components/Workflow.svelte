<!-- src/components/Workflow.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte';
 
/** 
   * Now we accept a pre-built list of stages,
   * each with its `name` and one of four statuses.
   */
  export let isRestartMode = true;

  export let stages: {
    name: string;
    status: 'pending' | 'active' | 'completed' | 'failed';
    description: string;
    longDescription: string;
  }[] = [];

  const dispatch = createEventDispatcher();

  function handleStepClick(stage: { name: string; status: string }) {
    if (isRestartMode && stage.status === 'completed') {
      dispatch('retrigger', { stage: stage.name });
    }
  }
  

</script>

<div class="workflow-table-container">
    <table class="workflow-table">
        <thead>
            <tr>
                <th>Stage</th>
                <th>Status</th>
                <th>Details</th>
                {#if isRestartMode}
                    <th class="action-header">Action</th>
                {/if}
            </tr>
        </thead>
        <tbody>
            {#each stages as stage}
                <tr class:active-row={stage.status === 'active'}>
                    <td class="stage-name"><strong>{stage.name}</strong></td>
                    <td>
                        <span class="status-badge" class:success={stage.status === 'completed'} class:active={stage.status === 'active'} class:failed={stage.status === 'failed'} class:pending={stage.status === 'pending'}>
                            {stage.status}
                        </span>
                    </td>
                    <td class="description">{stage.description}</td>
                    {#if isRestartMode}
                        <td class="action-cell">
                            {#if stage.status === 'completed'}
                                <button class="retrigger-button" on:click={() => handleStepClick(stage)}>
                                    Restart
                                </button>
                            {/if}
                        </td>
                    {/if}
                </tr>
            {/each}
        </tbody>
    </table>
</div>

<style>
.workflow-table-container {
  overflow-x: auto;
  background-color: #ffffff;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
  margin-top: 1.5rem;
}

.workflow-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 600px;
}

.workflow-table th, .workflow-table td {
  padding: 1rem 1.25rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.workflow-table th {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  color: #6b7280;
  letter-spacing: 0.05em;
}

.workflow-table tbody tr:last-child td {
  border-bottom: none;
}

.workflow-table tbody tr:hover {
  background-color: #f9fafb;
}

.workflow-table .active-row {
    background-color: #fefce8; /* yellow-50 */
    box-shadow: inset 4px 0 0 0 #facc15; /* yellow-400 */
}

.stage-name {
  font-weight: 600;
  color: #1f2937;
}

.description {
  font-size: 0.9rem;
  color: #4b5563;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: capitalize;
  white-space: nowrap;
}

.status-badge.pending {
  background-color: #f3f4f6;
  color: #4b5563;
}
.status-badge.completed, .status-badge.success {
  background-color: #d1fae5;
  color: #065f46;
}
.status-badge.active {
  background-color: #fef9c3;
  color: #92400e;
  animation: pulse 2s infinite;
}
.status-badge.failed {
  background-color: #fee2e2;
  color: #991b1b;
}

.action-header, .action-cell {
    text-align: center;
}

.retrigger-button {
  background: #f3f4f6;
  color: #1f2937;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.4rem 0.8rem;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retrigger-button:hover {
  background-color: #e5e7eb;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
</style>