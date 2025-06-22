<!-- src/components/GeneratedImages.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let generatedThumbnails: any[] = [];
  export let onDemandThumbnails: any[] = [];

  const dispatch = createEventDispatcher();

  function showImageModal(imageUrl: string) {
    dispatch('showImageModal', { imageUrl });
  }
</script>

<div class="detail-section">
  <h2>Generated Thumbnails</h2>
  <p class="section-description">Thumbnails created by the agent pipeline. Click an image to view it in full size.</p>

  {#if generatedThumbnails.length === 0 && onDemandThumbnails.length === 0}
    <p class="empty-state">No thumbnails have been generated for this video yet.</p>
  {:else}
    <div class="thumbnails-grid">
      {#each [...(generatedThumbnails || []), ...(onDemandThumbnails || [])] as thumb}
        {@const imageUrl = thumb.image_url}
        {#if imageUrl}
          <div class="thumbnail-item">
            <button type="button" class="thumbnail-image-wrapper" on:click={() => showImageModal(imageUrl)}>
              <img src={imageUrl} alt={thumb.prompt || 'Generated visual'}>
            </button>
            <div class="thumbnail-footer">
                <p>{thumb.prompt || 'No prompt'}</p>
            </div>
          </div>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<style>
  .detail-section { background-color: #ffffff; padding: 1.5rem; border-radius: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 2rem; }
  .detail-section h2 { font-size: 1.5rem; font-weight: 700; color: #1a202c; margin-bottom: 0.5rem; }
  .section-description { font-size: 0.9rem; color: #718096; margin-bottom: 1.5rem; }
  .thumbnails-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1.5rem; }
  .thumbnail-item { display: flex; flex-direction: column; border-radius: 0.75rem; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; }
  .thumbnail-item:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
  .thumbnail-image-wrapper { display: block; width: 100%; aspect-ratio: 16 / 9; cursor: pointer; border: none; padding: 0; background-color: #f7fafc; }
  .thumbnail-image-wrapper img { width: 100%; height: 100%; object-fit: cover; }
  .thumbnail-footer { background-color: #f9fafb; padding: 1rem; border-top: 1px solid #e2e8f0; flex-grow: 1; }
  .thumbnail-footer p { margin: 0; font-size: 0.85rem; color: #4a5568; line-height: 1.4; }
  .empty-state { color: #718096; text-align: center; padding: 2rem; background-color: #f9fafb; border-radius: 0.75rem; }
</style>