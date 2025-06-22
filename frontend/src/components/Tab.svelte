<script lang="ts">
  import { getContext } from 'svelte';
  import type { Writable } from 'svelte/store';

  export let id: any;
  export let title: string;

  interface TabContext {
    addTab: (tab: { id: any; title: string }) => void;
    activeTab: Writable<any>;
  }

  const { addTab, activeTab } = getContext<TabContext>('TABS_CONTEXT');

  addTab({ id, title });
</script>

{#if $activeTab === id}
  <div class="tab-content-panel" role="tabpanel">
    <slot></slot>
  </div>
{/if} 