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
  }[] = [];

  const dispatch = createEventDispatcher();

  function handleStepClick(stage: { name: string; status: string }) {
    if (isRestartMode && stage.status === 'completed') {
      dispatch('retrigger', { stage: stage.name });
    }
  }
  

</script>

<section class="workflow-section">
  <h3 class="text-lg font-semibold mb-4 text-gray-700">Live Workflow</h3>
  <div class="workflow-container">
   {#each stages as stage, i}
     <button
       type="button"
       class="workflow-step"
       class:success={stage.status === 'completed'}
       class:active={stage.status === 'active'}
       class:failed={stage.status === 'failed'}
       class:pending={stage.status === 'pending'}
       class:restart-active={isRestartMode && stage.status === 'completed'}
       on:click={() => handleStepClick(stage)}
      disabled={isRestartMode && stage.status !== 'completed'}
     >
       <div class="workflow-step-container">
        <span>{stage.name}</span>
        {#if isRestartMode && stage.status === 'completed'}
          <button class="retrigger-button" on:click|stopPropagation={() => handleStepClick(stage)}>
            Restart from here
          </button>
        {/if}
      </div>
     </button>

     {#if i < stages.length - 1}
       <div
        class="workflow-arrow"
         class:completed={stage.status === 'completed'}
       />
     {/if}
  {/each}
 </div>
</section>

<style>

.workflow-section {
  padding: 2rem;
  background-color: #ffffff;
  border-radius: 1rem;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
  margin-top: 2rem;
}

.workflow-container {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
}

button.workflow-step {
  all: unset;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 1.25rem;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 0.875rem;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  min-width: 120px;
  text-align: center;
  cursor: default;
  position: relative;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05);
}

.workflow-step.pending {
  background-color: #f1f5f9;
  color: #64748b;
  border-color: #e2e8f0;
}

.workflow-step.success {
  background-color: #ecfdf5;
  color: #047857;
  border-color: #34d399;
}

.workflow-step.active {
  background-color: #fef9c3;
  color: #92400e;
  border-color: #fde047;
  transform: scale(1.05);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
}

.workflow-step.failed {
  background-color: #fee2e2;
  color: #b91c1c;
  border-color: #f87171;
}

.workflow-step.restart-active {
  cursor: pointer;
  outline: 2px dashed #94a3b8;
  outline-offset: 4px;
}

.workflow-arrow {
  width: 24px;
  height: 2px;
  background-color: #94a3b8;
  position: relative;
  margin: 0 0.5rem;
}

.workflow-arrow::after {
  content: "";
  position: absolute;
  top: -4px;
  right: -4px;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  border-left: 6px solid #94a3b8;
}

.workflow-arrow.completed {
  background-color: #047857;
}

.workflow-arrow.completed::after {
  border-left-color: #047857;
}

.workflow-step-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.retrigger-button {
  margin-top: 0.5rem;
  background: #f3f4f6;
  color: #1f2937;
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  border-radius: 0.375rem;
  border: 1px solid #cbd5e1;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.retrigger-button:hover {
  background-color: #e5e7eb;
}

</style>