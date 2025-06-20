<script lang="ts">
  import type { Writable } from 'svelte/store';
  import Swal from 'sweetalert2';
  import { sanitizeTitleForFilename } from '../lib/utils';
  import { getHeaders } from '../lib/api';
  import { onMount } from 'svelte';
  import RangeSlider from 'svelte-range-slider-pips';

  // --- Props ---
  export let candidates: any[] = [];
  export let videoId: string;
  export let videoData: any;
  
  // --- Local State ---
  let shortsWithState: any[] = [];

  onMount(() => {
    // When the component loads, fetch temporary URLs for any clips that are already saved.
    shortsWithState.forEach((short, index) => {
        if (short.isSaved && short.generated_gcs_uri && !short.generated_clip_url) {
            fetchPlayableUrl(index);
        }
    });
  });

  async function fetchPlayableUrl(index: number) {
      const short = shortsWithState[index];
      try {
          const response = await fetch(`/api/clip/url?gcs_uri=${encodeURIComponent(short.generated_gcs_uri)}`, {
              headers: await getHeaders(),
          });
          if (response.ok) {
              const data = await response.json();
              const newShorts = [...shortsWithState];
              newShorts[index].generated_clip_url = data.url;
              shortsWithState = newShorts;
          }
      } catch (e) {
          console.error("Failed to fetch clip URL", e);
      }
  }

  // Reactive statement to update local state when props change
  $: {
    const generatedClips = videoData?.generated_clips || [];
    shortsWithState = (candidates || []).map(c => {
      const existingClip = generatedClips.find((gc: any) => 
        parseFloat(gc.start_time) === parseFloat(c.start_time) && 
        parseFloat(gc.end_time) === parseFloat(c.end_time)
      );
      return {
        ...c,
        isGenerating: false,
        isGeneratingPreview: false,
        isPreviewing: false,
        isSaving: false,
        isSaved: !!existingClip,
        editedStartTime: parseFloat(c.start_time),
        editedEndTime: parseFloat(c.end_time),
        preview_url: null,
        preview_duration: 0,
        slider_values: [parseFloat(c.start_time), parseFloat(c.end_time)],
        generated_clip_url: null, // Fetched on demand
        generated_gcs_uri: existingClip?.clip_gcs_uri,
      };
    });
  }

  // --- Methods ---
  async function generatePreview(index: number) {
    const short = shortsWithState[index];
    short.isGeneratingPreview = true;
    try {
      const res = await fetch(`/api/video/${videoId}/generate-preview-clip`, {
        method: 'POST',
        headers: await getHeaders(),
        body: JSON.stringify({ start_time: short.start_time, end_time: short.end_time })
      });
      const data = await res.json();
      short.preview_url = data.preview_url;
      short.isPreviewing = true;
    } catch(e) {
      Swal.fire('Error', 'Could not generate preview clip.', 'error');
    } finally {
      short.isGeneratingPreview = false;
    }
  }

  function handleVideoLoaded(e: Event, index: number) {
    const video = e.target as HTMLVideoElement;
    const short = shortsWithState[index];
    short.preview_duration = video.duration;
    // The original clip's times relative to the new *preview* clip
    const relative_start = short.start_time - Math.max(0, short.start_time - 30);
    const relative_end = relative_start + (short.end_time - short.start_time);
    short.slider_values = [relative_start, relative_end];
  }

  async function generateFinalClip(index: number) {
    const short = shortsWithState[index];
    short.isGenerating = true;

    const preview_start_offset = Math.max(0, short.start_time - 30);
    const final_start_time = preview_start_offset + short.slider_values[0];
    const final_end_time = preview_start_offset + short.slider_values[1];

    try {
      const response = await fetch(`/api/video/${videoId}/generate-clip`, {
          method: 'POST',
          headers: await getHeaders(),
          body: JSON.stringify({
              start_time: final_start_time,
              end_time: final_end_time,
              suggested_title: short.suggested_title
          })
      });
      const data = await response.json();
      short.generated_clip_url = data.clip_url;
      short.generated_gcs_uri = data.clip_gcs_uri;
      
      await saveClip(index, final_start_time, final_end_time);

    } catch (e) {
      Swal.fire('Error', 'Could not generate final clip.', 'error');
    } finally {
      short.isGenerating = false;
    }
  }

  async function saveClip(index: number, final_start_time: number, final_end_time: number) {
    const short = shortsWithState[index];
    if (!short || !short.generated_gcs_uri) return;
    short.isSaving = true;
    try {
        await fetch(`/api/video/${videoId}/save-clip`, {
            method: 'POST',
            headers: await getHeaders(),
            body: JSON.stringify({
                start_time: final_start_time,
                end_time: final_end_time,
                title: short.suggested_title,
                clip_gcs_uri: short.generated_gcs_uri
            })
        });
        short.isSaved = true;
    } catch (e) {
        console.error('Failed to save clip:', e);
    } finally {
        short.isSaving = false;
    }
  }
</script>

<div class="detail-section" id="shorts-candidates">
  {#if shortsWithState && shortsWithState.length > 0}
    <ul class="shorts-list">
      {#each shortsWithState as short, index}
        <li class="short-candidate-item">
          <div class="short-info">
            <h4>{short.suggested_title}</h4>
            <p><strong>Reason:</strong> {short.reason}</p>
            {#if short.transcript_snippet}
              <p class="snippet"><em>"{short.transcript_snippet}"</em></p>
            {/if}
          </div>
          <div class="short-actions">
            {#if short.isPreviewing}
              <div class="phone-mask">
                <div class="phone-notch"></div>
                <div class="clip-preview-container">
                    <video 
                      src={short.preview_url} 
                      preload="auto"
                      on:loadedmetadata={(e) => handleVideoLoaded(e, index)}
                      controls
                    >
                      <track kind="captions" />
                    </video>
                </div>
              </div>

              {#if short.preview_duration > 0}
              <div class="slider-container">
                <RangeSlider 
                  bind:values={short.slider_values} 
                  min={0} 
                  max={short.preview_duration} 
                  step={0.1}
                  pips
                  all="label"
                />
              </div>
              {/if}

              <div class="clip-buttons">
                <button on:click={() => generateFinalClip(index)} disabled={short.isGenerating}>
                  Download Final Clip
                </button>
              </div>

            {:else if short.isSaved}
                {#if short.generated_clip_url}
                    <div class="phone-mask">
                        <div class="phone-notch"></div>
                        <div class="clip-preview-container">
                            <video controls src={short.generated_clip_url} preload="metadata">
                                <track kind="captions" />
                            </video>
                        </div>
                    </div>
                    <p><em>This clip has been saved.</em></p>
                {:else}
                    <p>Loading saved clip...</p>
                {/if}
               
            {:else}
              <button on:click={() => generatePreview(index)} disabled={short.isGeneratingPreview}>
                {#if short.isGeneratingPreview}Generating Preview...{:else}Generate Preview & Edit{/if}
              </button>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {:else}
    <p>No shorts candidates were identified for this video.</p>
  {/if}
</div>

<style>
  .shorts-list {
    list-style: none;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .short-candidate-item {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 2rem;
    padding: 1.5rem;
    background-color: #f8fafc;
    border-radius: 0.5rem;
    border: 1px solid #e2e8f0;
    align-items: center;
  }

  .short-info h4 {
    margin: 0 0 0.5rem 0;
    font-size: 1.2rem;
    color: #374151;
  }

  .short-info p {
    margin: 0.5rem 0;
    color: #475569;
    line-height: 1.5;
  }
  .short-info .snippet {
    color: #64748b;
    font-size: 0.95rem;
    border-left: 3px solid #e2e8f0;
    padding-left: 1rem;
    margin-top: 1rem;
  }

  .short-actions {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
  }
  
  .clip-preview-container {
    width: 100%;
    height: 100%;
    border-radius: 20px; /* Match the inner radius */
    overflow: hidden;
    position: relative;
    z-index: 1;
  }

  .clip-preview-container video {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .clip-buttons {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .phone-mask {
    position: relative;
    width: 220px; /* Adjust width as needed */
    height: 450px; /* Adjust height for a phone-like aspect ratio */
    background-color: #111;
    border-radius: 30px;
    padding: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden; /* This will round the video corners */
  }

  .phone-notch {
    position: absolute;
    top: 10px;
    width: 40%;
    height: 15px;
    background-color: #111;
    border-radius: 0 0 10px 10px;
    z-index: 2;
  }

  .button-save {
    background-color: #e0e7ff;
    border: 1px solid #c7d2fe;
    color: #4338ca;
  }
  .button-save:hover {
    background-color: #c7d2fe;
  }

  /* Standard button styles from VideoDetail.svelte */
  :global(.button-secondary) {
    background: none;
    border: 1px solid #d1d5db;
    color: #475569;
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: background-color 0.2s, color 0.2s;
    text-decoration: none;
  }
  :global(.button-secondary:hover) {
    background-color: #f3f4f6;
    border-color: #9ca3af;
  }
  :global(.button-danger) {
    background-color: #fee2e2;
    border: 1px solid #fecaca;
    color: #b91c1c;
  }
  :global(.button-danger:hover) {
    background-color: #fecaca;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .short-candidate-item {
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
    .short-actions {
      align-items: flex-start;
    }
  }

  .slider-container {
    width: 100%;
    margin-top: 1.5rem;
    padding: 0 1rem;
  }
</style> 