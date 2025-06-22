<script lang="ts">
  import { setContext } from 'svelte';
  import { writable } from 'svelte/store';

  export let activeTabId: any;

  const tabInfos = writable<{ id: any; title: string }[]>([]);
  const activeTab = writable(activeTabId);

  // Allow the parent to control the active tab
  $: activeTab.set(activeTabId);

  // Allow for two-way binding
  activeTab.subscribe(value => {
    activeTabId = value;
  });

  setContext('TABS_CONTEXT', {
    addTab: (tab: { id: any; title: string }) => {
      tabInfos.update(infos => [...infos, tab]);
    },
    activeTab
  });
</script>

<div class="tabs">
  {#each $tabInfos as tab}
    <button
      class="tab-button"
      class:active={$activeTab === tab.id}
      on:click={() => activeTab.set(tab.id)}
    >
      {tab.title}
    </button>
  {/each}
</div>

<div class="tabs-content">
  <slot></slot>
</div>

<style>
.tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 2rem;
}
.tab-button {
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  border: none;
  background: none;
  font-size: 1rem;
  font-weight: 600;
  color: #6b7280;
  border-bottom: 3px solid transparent;
  transition: color 0.2s, border-color 0.2s;
}
.tab-button:hover {
  color: #374151;
}
.tab-button.active {
  color: #4F46E5;
  border-bottom-color: #4F46E5;
}
.tabs-content {
  padding-top: 1rem;
}
</style> 