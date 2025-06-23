<script lang="ts">
  import { onMount } from 'svelte';
  import Swal from 'sweetalert2';
  import { marked } from 'marked';

 

  import { listenForUpdates, retriggerStage } from '../lib/api';
  import { videoStatus } from '../lib/stores';
  import { sanitizeTitleForFilename } from '../lib/utils';
      // ... other imports
    
  import GeneratedImages from '../components/GeneratedImages.svelte'; // <-- ADD THIS LINE
  import ShortsCandidates from '../components/ShortsCandidates.svelte';
  import WorkflowManager from '../components/WorkflowManager.svelte';
  import Tabs from '../components/Tabs.svelte';
  import Tab from '../components/Tab.svelte';

  export let params: { id?: string } = {};

  // --- State ---
  let videoData: any = null;
  let isLoading = true;
  let errorMessage = '';
  let activeTab = 'overview';

  let modalImageUrl = '';
  let substackHtml = '';
  let isLoadingSubstack = false;
  
  let newsletterPreImageHtml = '';
  let newsletterPostImageHtml = '';
  let availableImages: string[] = [];
  let isImageSelectorVisible = false;
  let selectedNewsletterImage = '';
  let isWorkflowVisible = false; // New state for collapsibility
  let isImageModalVisible = false;

  const stagesMetadata = [
    { name: 'Ingestion', description: 'Downloading & preparing the video file.', longDescription: 'The system is downloading the video from its source URL and preparing it for the pipeline by placing it in cloud storage.' },
    { name: 'Transcription', description: 'Converting audio to text.', longDescription: 'Using an AI model to transcribe the spoken audio from the video into a text document. This forms the basis for all other content.' },
    { name: 'Analysis', description: 'Identifying key topics and clips.', longDescription: 'The transcript is being analyzed by an AI to identify the main topics, key concepts, and potential segments suitable for short-form video clips.' },
    { name: 'Copywriting', description: 'Generating social media posts.', longDescription: 'AI is generating various pieces of marketing copy, such as posts for social media platforms and email newsletters, based on the video content.' },
    { name: 'Visuals', description: 'Creating thumbnail images.', longDescription: 'AI is generating a set of compelling thumbnail images that are thematically aligned with the video content to attract viewers.' },
    { name: 'Publishing', description: 'Finalizing and marking as complete.', longDescription: 'All assets have been generated. In a real-world scenario, this step would upload the content to its final destination (e.g., YouTube). Here, it marks the process as complete.' }
  ];

  // This is a placeholder now, as the WorkflowManager handles the logic.
  const workflowStages = [];

  // --- Lifecycle ---
  onMount(() => {
    loadVideoDetails();
    if (params.id) {
      const eventSource = listenForUpdates(params.id);
      // Return a cleanup function to close the connection when the component is destroyed
      return () => {
        eventSource?.close();
      };
    }
  });

  // This reactive statement is the key: it updates our local videoData
  // whenever the videoStatus store (which is updated by the SSE) changes.
  $: if ($videoStatus && $videoStatus.video_id === params.id) {
    videoData = { ...videoData, ...$videoStatus };
  }

  $: if (activeTab === 'copy') {
    loadSubstackContent();
  }

  $: {
    if (activeTab === 'copy' && videoData) {
        availableImages = [
            ...(videoData.structured_data?.generated_thumbnails || []),
            ...(videoData.structured_data?.quote_visuals || []),
            ...(videoData.structured_data?.on_demand_thumbnails || [])
        ].map(t => t.image_url).filter(Boolean);

        if(videoData.marketing_copy?.email_newsletter) {
            let markdownBody = '';
            if (typeof videoData.marketing_copy.email_newsletter === 'object' && videoData.marketing_copy.email_newsletter.body) {
                markdownBody = videoData.marketing_copy.email_newsletter.body;
            } else if (typeof videoData.marketing_copy.email_newsletter === 'string') {
                markdownBody = videoData.marketing_copy.email_newsletter;
            }

            const parts = markdownBody.split(/\[Image\]/g);
            newsletterPreImageHtml = marked(parts[0]) as string;
            if (parts.length > 1) {
                newsletterPostImageHtml = marked(parts.slice(1).join('')) as string;
            } else {
                newsletterPostImageHtml = '';
            }
        }
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
        if (isImageModalVisible) isImageModalVisible = false;
        if (isImageSelectorVisible) isImageSelectorVisible = false;
    }
  }

  // --- Data Loading ---
  async function loadVideoDetails() {
    console.log(`[VideoDetail] loadVideoDetails called for video ID: ${params.id}`);
    if (!params.id) {
      errorMessage = 'No video ID specified.';
      isLoading = false;
      return;
    }
    
    isLoading = true;
    try {
      const response = await fetch(`/api/video/${params.id}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      videoData = data.video;
    } catch (error: any) {
      errorMessage = 'Could not load video details. Please try again later.';
      console.error('Failed to load video details:', error);
    } finally {
      isLoading = false;
    }
  }

  async function loadSubstackContent() {
    if (!videoData?.substack_gcs_uri || isLoadingSubstack || substackHtml) return;
    
    isLoadingSubstack = true;
    try {
        const url = videoData.substack_gcs_uri.replace("gs://", "https://storage.googleapis.com/");
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch article content.');
        const markdown = await response.text();
        substackHtml = marked(markdown) as string;
    } catch (error) {
        console.error("Error loading Substack content:", error);
        // Optionally, show an error message to the user
    } finally {
        isLoadingSubstack = false;
    }
  }

  // --- Helpers ---
  function getStatusClass(status: string): string {
    if (!status) return 'status-unknown';
    if (status.includes('failed')) return 'status-failed';
    if (status === 'published' || status.includes('completed') || status.includes('generated')) return 'status-success';
    if (status) return 'status-in-progress';
    return 'status-unknown';
  }

  // --- Event Handlers ---
  function showImageModal(event: CustomEvent) {
    modalImageUrl = event.detail.imageUrl;
    isImageModalVisible = true;
  }
  
  
  function handleNewOnDemandImage(event: CustomEvent) {
    const newImage = event.detail;
    if (videoData && videoData.structured_data) {
      if (!videoData.structured_data.on_demand_thumbnails) {
        videoData.structured_data.on_demand_thumbnails = [];
      }
      videoData.structured_data.on_demand_thumbnails.push(newImage);
      // Trigger Svelte's reactivity
      videoData = videoData;
    }
  }

  async function handleRetrigger(event: CustomEvent<{ stage: string }>) {
    const stageToRestart = event.detail.stage;
    if (!params.id) {
        Swal.fire('Error', 'Cannot re-trigger: Video ID is missing.', 'error');
        return;
    }

    try {
        await retriggerStage(params.id, stageToRestart);
        Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'success',
            title: `'${stageToRestart}' stage has been successfully restarted.`,
            showConfirmButton: false,
            timer: 3000
        });
    } catch (error: any) {
        Swal.fire('Error', `Failed to restart stage: ${error.message}`, 'error');
    }
  }

  function handleTabChange(e: any) {
    activeTab = e.detail.id;
  }

  function selectImageForNewsletter(imageUrl: string) {
    selectedNewsletterImage = imageUrl;
    isImageSelectorVisible = false;
  }

</script>

<svelte:window on:keydown={handleKeydown}/>

{#if isLoading}
  <div class="loader-container"><div class="loader"></div></div>
{:else if errorMessage}
  <p class="error-message">{errorMessage}</p>
{:else if videoData}
  

  <div class="container">
    <div class="video-header">
        <h1 class="video-title">{videoData.video_title}</h1>
        <span class="status-badge-lg-{getStatusClass(videoData.status)}">{videoData.status_message}</span>
    </div>

    <!-- Workflow Visualization -->
    <div class="section">
        <div class="section-header">
            <h2 class="section-title">Workflow Status</h2>
            <button class="toggle-button" on:click={() => isWorkflowVisible = !isWorkflowVisible}>
                {isWorkflowVisible ? 'Hide' : 'Show'}
            </button>
        </div>
        {#if isWorkflowVisible}
            <WorkflowManager video={videoData} stagesMetadata={stagesMetadata} on:retrigger={handleRetrigger} />
        {/if}
    </div>

    <!-- Tabs for different sections -->
    <Tabs bind:activeTabId={activeTab}>
        <Tab id="overview" title="Overview">
          <div class="tab-content active">
            <div class="overview-grid">
                 <div class="video-player-wrapper">
                    <iframe
                        class="youtube-iframe"
                        src={`https://www.youtube.com/embed/${videoData.video_id}`}
                        title="YouTube video player"
                        frameborder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowfullscreen
                    ></iframe>
                </div>
                {#if videoData.structured_data?.summary}
                <div class="detail-section" id="summary-section">
                    <h2>Summary</h2>
                    <p>{videoData.structured_data.summary}</p>
                </div>
                {/if}
            </div>
          </div>
        </Tab>
        <Tab id="images" title="Generated Images">
          <GeneratedImages
            videoId={params.id}
            videoSummary={videoData.structured_data?.summary || ''}
            generatedThumbnails={videoData.structured_data?.generated_thumbnails || []}
            onDemandThumbnails={videoData.structured_data?.on_demand_thumbnails || []}
            on:newOnDemandImage={handleNewOnDemandImage}
            on:showImageModal={showImageModal}
          />
        </Tab>
        <Tab id="copy" title="Generated Copy">
          <div class="tab-content active">
            {#if videoData.marketing_copy}
            <div class="detail-section">
                <h2>Generated Copy</h2>
                <div class="copy-assets">
                    {#if videoData.marketing_copy.facebook_post}
                    <div class="copy-asset-card">
                        <h4>Facebook / Instagram Post</h4>
                        <div class="copy-text">{@html videoData.marketing_copy.facebook_post}</div>
                    </div>
                    {/if}
                     {#if videoData.marketing_copy.email_newsletter}
                     <div class="copy-asset-card">
                        <h4>Email Newsletter</h4>
                        {#if typeof videoData.marketing_copy.email_newsletter === 'object'}
                            <h5 class="newsletter-subject">{videoData.marketing_copy.email_newsletter.subject}</h5>
                        {/if}
                        <div class="copy-text newsletter-container">
                            {@html newsletterPreImageHtml}
                            
                            {#if selectedNewsletterImage}
                                <img src={selectedNewsletterImage} alt="Selected newsletter visual" class="newsletter-image">
                            {:else if availableImages.length > 0}
                                <div class="image-placeholder">
                                    <button class="button-secondary" on:click={() => isImageSelectorVisible = true}>
                                        Select an Image
                                    </button>
                                </div>
                            {/if}
    
                            {@html newsletterPostImageHtml}
                         </div>
                     </div>
                     {/if}
                </div>
            </div>
            {/if}
    
            {#if videoData.substack_gcs_uri}
             <div class="detail-section">
                <h2>Substack Article</h2>
                <div class="substack-preview">
                    {#if isLoadingSubstack}
                        <div class="loader-small"></div>
                    {:else if substackHtml}
                        <div class="copy-text">
                            {@html substackHtml}
                        </div>
                    {/if}
                </div>
                <a href={videoData.substack_gcs_uri.replace("gs://", "https://storage.googleapis.com/")} class="button-link" download>
                    Download Formatted Article
                </a>
             </div>
            {/if}
    
            {#if !videoData.marketing_copy && !videoData.substack_gcs_uri}
                <div class="detail-section">
                    <p>No generated copy is available for this video yet.</p>
                </div>
            {/if}
        </div>
        </Tab>
        <Tab id="shorts" title="Shorts Candidates">
          <div class="tab-content active">
             <!-- Shorts content will go here -->
            <ShortsCandidates videoId={videoData.video_id} candidates={videoData.structured_data?.shorts_candidates || []} />
         </div>
        </Tab>
    </Tabs>
  </div>
{/if}

<!-- Image Modal -->
{#if isImageModalVisible}
<div class="modal-overlay" role="dialog" aria-modal="true" on:click={() => isImageModalVisible = false}>
    <button type="button" class="modal-close-button" on:click={() => isImageModalVisible = false}>&times;</button>
    <img class="modal-content-image" src={modalImageUrl} alt="Full size generated visual">
</div>
{/if}

<!-- Image Selector Modal -->
{#if isImageSelectorVisible}
<div class="modal-overlay" role="dialog" aria-modal="true" on:click={() => isImageSelectorVisible = false}>
    <div class="modal-content" role="document" on:click|stopPropagation>
        <div class="modal-header">
            <h3>Select an Image</h3>
            <button type="button" class="modal-close-button" on:click={() => isImageSelectorVisible = false}>&times;</button>
        </div>
        <div class="modal-body">
            <div class="thumbnails-grid">
                 {#each availableImages as imageUrl}
                    <button class="thumbnail-selector" on:click={() => selectImageForNewsletter(imageUrl)}>
                        <img src={imageUrl} alt="Selectable thumbnail">
                    </button>
                 {/each}
            </div>
        </div>
    </div>
</div>
{/if}

<style>
/* Base Layout */
.container {
    max-width: 1200px;
    min-height: 90vh;
    margin: 0 auto;
    padding: clamp(1rem, 5vw, 2.5rem);
    font-family: 'Inter', sans-serif;
    background-color: #ffffff;
    border-radius: 0.75rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
}

.loader {
    border: 8px solid #f3f3f3;
    border-top: 8px solid #4F46E5;
    border-radius: 50%;
    width: 60px;
    height: 60px;
    animation: spin 1s linear infinite;
    margin: 4rem auto;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Header */
.video-header {
    margin-bottom: 2rem;
}
.video-title {
    font-size: 2.5rem;
    font-weight: 800;
    color: #4F46E5;
    line-height: 1.2;
}

/* Tabs */
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

/* Content Sections */
.tab-content.active {
    display: block;
}
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}
.detail-section {
    margin-bottom: 3rem;
}
.detail-section h2, .section-title {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0;
    color: #374151;
}
.section-description {
    font-size: 1rem;
    color: #64748b;
    max-width: 700px;
    margin-bottom: 1.5rem;
}

/* Overview Tab */
.overview-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 2rem;
    align-items: flex-start;
}
.video-player-wrapper {
    position: relative;
    padding-top: 56.25%; /* 16:9 Aspect Ratio */
    background-color: #000;
    border-radius: 0.5rem;
    overflow: hidden;
}
.youtube-iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}

/* Assets Tab */
.thumbnails-grid {
  display: flex;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); /* ⬅️ tighter minimum */
  gap: 0.2rem; /* ⬅️ less space between cards */
  max-width: 1000px; /* ⬆️ slightly looser max if you want more breathing room */
  margin: 0 auto;
  align-items: flex-start;
}

.thumbnail-item {
  background-color: #fff;
  min-width: 100px;
  max-width: 250px;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08); /* ⬆️ stronger depth */
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.thumbnail-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.1);
}

.thumbnail-image-wrapper {
  aspect-ratio: 1 / 1;
  background-color: #f1f5f9;
  overflow: hidden;
  border: none;
  padding: 0;
  transition: background-color 0.2s ease;
}



.thumbnail-image-wrapper:hover {
  background-color: #e2e8f0;
}
.thumbnail-footer {
  padding: 0.75rem 1rem;
  background-color: #f9fafb;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: flex-start;
  
  font-size: 0.9rem;
  color: #475569;
  font-weight: 500;
}

.preview-post-btn {
    width: 100%;
}
.delete-img {
  background: none;
  border: none;
  color: #dc2626; /* Tailwind's red-600 */
  font-size: 1.25rem;
  line-height: 1;
  font-weight: bold;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  transition: background-color 0.2s ease, color 0.2s ease;
  margin-left: auto; /* Pushes it to the right in flex containers */
}

.delete-img:hover {
  background-color: #fee2e2; /* red-100 */
  color: #b91c1c; /* red-700 */
}


.thumbnail-prompt {
    padding: 1rem;
    flex-grow: 1; /* Allows the bottom part to fill space if needed */
}
.thumbnail-prompt h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
    color: #374151;
}
.thumbnail-prompt p {
    margin: 0 0 1rem 0;
    font-size: 0.9rem;
    color: #64748b;
    line-height: 1.5;
}

.copy-assets {
    display: grid;
    gap: 1.5rem;
}

.copy-asset-card {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    padding: 1.5rem;
}
.copy-asset-card h4 {
    margin: 0 0 1rem 0;
    font-size: 1.1rem;
}
.newsletter-subject {
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e2e8f0;
}
.copy-text {
    background: white;
    padding: 1rem;
    border-radius: 0.25rem;
    border: 1px solid #e2e8f0;
    line-height: 1.6;
    color: #374151;
}

.copy-text.newsletter-container {
    overflow: auto; /* Simple clearfix to contain the floated element */
}

.newsletter-image {
    float: right;
    width: 250px;
    max-width: 40%;
    border-radius: 8px;
    margin-left: 1.5rem;
    margin-bottom: 1rem;
}

.image-placeholder {
    float: right;
    width: 250px;
    max-width: 40%;
    min-height: 220px;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2rem;
    margin-left: 1.5rem;
    margin-bottom: 1rem;
    border: 2px dashed #e2e8f0;
    border-radius: 8px;
    background-color: #f8fafc;
}

/* Modal */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}
.modal-close-button {
    position: absolute;
    top: 20px;
    right: 30px;
    font-size: 2.5rem;
    color: white;
    cursor: pointer;
    background: none;
    border: none;
    line-height: 1;
}
.modal-content-image {
    max-width: 90vw;
    max-height: 90vh;
    object-fit: contain;
}

.modal-content {
    background: white;
    padding: 1.5rem;
    border-radius: 0.5rem;
    max-width: 800px;
    width: 90%;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
}

.modal-header h3 {
    margin: 0;
    font-size: 1.5rem;
}

.modal-body {
    overflow-y: auto;
}

.thumbnail-selector {
    border: 2px solid transparent;
    border-radius: 0.5rem;
    padding: 0;
    cursor: pointer;
    overflow: hidden;
    transition: border-color 0.2s;
}
.thumbnail-selector:hover {
    border-color: #4F46E5;
}
.thumbnail-selector img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

/* Buttons */
.button-secondary {
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
.button-secondary:hover {
    background-color: #f3f4f6;
    border-color: #9ca3af;
}

/* Social Preview */
:global(.social-preview-popup) {
    max-width: 700px;
    min-width: 600px;
   
    min-height: 300px;
}
.social-preview-caption {
    text-align: left;
    margin-top: 1rem;
    padding: 1rem;
    background-color: #f8fafc;
    border-radius: 0.5rem;
    max-height: 200px;
    overflow-y: auto;
    font-size: 0.95rem;
    line-height: 1.5;
}

.on-demand-controls {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
}
.control-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
select {
    padding: 0.5rem;
    border-radius: 0.375rem;
    border: 1px solid #d1d5db;
    background-color: white;
    font-family: inherit;
    font-size: 0.9rem;
}

.new-prompts-list {
    list-style: none;
    padding: 0;
    margin-top: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.new-prompts-list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background-color: #f8fafc;
    border-radius: 0.5rem;
    border: 1px solid #e2e8f0;
    gap: 1rem;
}

.new-prompts-list li.generating {
    opacity: 0.5;
    pointer-events: none;
}

.prompt-text {
    flex-grow: 1;
    margin-right: 1rem;
    color: #374151;
    line-height: 1.5;
}

.prompt-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-shrink: 0;
}

.prompt-input {
    flex-grow: 1;
    margin-right: 1rem;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 0.9rem;
}

.prompt-editing-controls {
    margin-bottom: 1rem;
    display: flex;
    justify-content: flex-end;
}

/* --- Responsive Design --- */
@media (max-width: 768px) {
    .container {
        padding: 1rem;
    }

    .video-title {
        font-size: 2rem;
    }

    .overview-grid {
        grid-template-columns: 1fr;
    }

    .thumbnails-grid {
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    }
    
    .new-prompts-list li {
        flex-direction: column;
        align-items: stretch;
        gap: 1rem;
    }

    .prompt-controls {
        justify-content: space-between;
    }
}

.substack-preview {
    margin-bottom: 1rem;
}

.loader-small {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #4F46E5;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin: 2rem auto;
}

.toggle-button {
  background: none;
  border: 1px solid #d1d5db;
  color: #475569;
  padding: 0.25rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 9999px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.toggle-button:hover {
    background-color: #f3f4f6;
}

.rotated {
    transform: rotate(180deg);
  }
  .workflow-toggle-container {
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: flex-start;
  }

  .workflow-toggle-button {
    background-color: #f3f4f6;
    color: #4b5563;
    font-weight: 600;
    padding: 0.5rem 1rem;
    border-radius: 9999px;
    border: 1px solid #e5e7eb;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    transition: background-color 0.2s;
  }
  .workflow-toggle-button:hover {
    background-color: #e5e7eb;
  }
    .workflow-toggle-button svg {
        transition: transform 0.2s;
        width: 1.25rem;
        height: 1.25rem;
    }
</style>

