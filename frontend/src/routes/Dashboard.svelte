<!-- src/routes/Dashboard.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Swal from 'sweetalert2';
  import { accessToken } from '../lib/auth';

  interface Video {
    video_id: string;
    video_title: string;
    video_url: string;
    status: string;
    received_at?: string;
    substack_hook?: string;
    structured_data?: {
      summary?: string;
    };
    thumbnails?: string[];
  }

  let videos: Video[] = [];
  let isLoading = true;
  let errorMessage = '';
  let activeMenu = ''; // Holds the video_id of the active menu

  onMount(async () => {
    try {
      const token = $accessToken;
      if (!token) {
        // This can happen if the user's session expires or they log out.
        // We'll just show an empty dashboard.
        videos = [];
        isLoading = false;
        return;
      }

      const response = await fetch('/api/videos', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      videos = data.videos || [];
    } catch (error: any) {
      errorMessage = 'Could not load video data. Please try again later.';
      console.error('Failed to load videos:', error);
    } finally {
      isLoading = false;
    }
  });

  function getHook(video: Video): string {
    if (video.substack_hook) {
      return video.substack_hook;
    }
    if (video.structured_data?.summary) {
      return video.structured_data.summary.substring(0, 100) + '...';
    }
    return 'No hook or summary available.';
  }

  function getDisplayStatus(video: Video): { text: string; class: string } {
    const status = video.status;

    // If visuals failed but user generated some manually, consider it a success.
    if (status === 'visuals_failed' && video.thumbnails && video.thumbnails.length > 0) {
      return { text: 'Visuals Generated', class: 'status-success' };
    }
    
    const statusText = status.replace(/_/g, ' ');

    if (status.includes('failed')) return { text: statusText, class: 'status-failed' };
    if (status === 'published' || status.includes('completed') || status.includes('generated')) return { text: statusText, class: 'status-success' };
    if (status) return { text: statusText, class: 'status-in-progress' };
    
    return { text: 'Unknown', class: 'status-unknown' };
  }

  function confirmAndReprocess(event: MouseEvent, videoId: string, videoUrl: string) {
    event.stopPropagation();
    Swal.fire({
      title: 'Are you sure?',
      text: "This will delete all existing data and re-process the video from scratch. This cannot be undone.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Yes, reprocess it!',
      confirmButtonColor: '#DC2626',
      cancelButtonColor: '#64748B'
    }).then((result) => {
      if (result.isConfirmed) {
        localStorage.setItem('reprocessUrl', videoUrl);
        push('/');
      }
    });
  }
  
  async function retriggerStage(event: MouseEvent, videoId: string) {
    event.stopPropagation();
    activeMenu = ''; // Close menu

    const { value: stage } = await Swal.fire({
      title: 'Select a stage to re-trigger',
      input: 'select',
      inputOptions: {
        'transcription': 'Transcription',
        'analysis': 'Analysis',
        'copywriting': 'Copywriting',
        'visuals': 'Visuals'
      },
      inputPlaceholder: 'Select a stage',
      showCancelButton: true,
      confirmButtonText: 'Re-trigger',
    });

    if (stage) {
      try {
        const response = await fetch('/api/re-trigger', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_id: videoId, stage: stage })
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || 'Failed to re-trigger stage.');
        }

        Swal.fire({
          toast: true,
          position: 'top-end',
          icon: 'success',
          title: `Stage '${stage}' re-triggered!`,
          showConfirmButton: false,
          timer: 3000
        });

      } catch (error: any) {
        Swal.fire('Error', error.message, 'error');
      }
    }
  }

  async function handleCleanup() {
      const result = await Swal.fire({
          title: 'Are you sure?',
          text: "This will permanently delete all cached video files from the server.",
          icon: 'warning',
          showCancelButton: true,
          confirmButtonColor: '#d33',
          cancelButtonColor: '#3085d6',
          confirmButtonText: 'Yes, clean it up!'
      });

      if (result.isConfirmed) {
          Swal.fire({
              title: 'Cleaning...',
              text: 'Please wait while the server cleans up the files.',
              allowOutsideClick: false,
              didOpen: () => {
                  Swal.showLoading();
              }
          });

          try {
              const response = await fetch('/api/cleanup-cache', {
                  method: 'POST',
              });
              const data = await response.json();

              if (response.ok) {
                  Swal.fire('Cleaned!', data.message, 'success');
              } else {
                  throw new Error(data.message || 'Failed to clean up cache.');
              }
          } catch (error: any) {
              console.error('Cleanup error:', error);
              Swal.fire('Error!', `An error occurred: ${error.message}`, 'error');
          }
      }
  }
</script>

<div class="dashboard-container">
    <h1>Content Dashboard</h1>
    <p>Review and manage all processed video content.</p>
    
    {#if isLoading}
        <p>Loading videos...</p>
    {:else if errorMessage}
        <p class="error-message">{errorMessage}</p>
    {:else if videos.length === 0}
        <p>No processed videos found.</p>
    {:else}
        <div class="videos-grid">
            {#each videos as video (video.video_id)}
                {@const displayStatus = getDisplayStatus(video)}
                <a href={`#/video/${video.video_id}`} class="video-card">
                    <div class="card-thumbnail">
                        <img src={`https://img.youtube.com/vi/${video.video_id}/hqdefault.jpg`} alt="Video thumbnail">
                        <span class="card-status {displayStatus.class}">
                            {displayStatus.text}
                        </span>
                    </div>
                    <div class="card-content">
                        <h3 class="card-title">{video.video_title || 'Untitled Video'}</h3>
                        <p class="card-hook">{getHook(video)}</p>
                    </div>
                    <div class="card-footer">
                        <div class="footer-thumbnails">
                            {#if video.thumbnails && video.thumbnails.length > 0}
                                {#each video.thumbnails as thumbUrl}
                                    <div class="footer-thumbnail" style="background-image: url({thumbUrl})"></div>
                                {/each}
                            {:else}
                                <div class="footer-thumbnail-placeholder"></div>
                                <div class="footer-thumbnail-placeholder"></div>
                                <div class="footer-thumbnail-placeholder"></div>
                                <div class="footer-thumbnail-placeholder"></div>
                            {/if}
                        </div>
                        <div class="footer-meta">
                            <span class="processed-date">
                                Processed: {video.received_at ? new Date(video.received_at).toLocaleDateString() : 'Not available'}
                            </span>
                            
                            <div class="actions-menu-container">
                                <button class="actions-button" on:click|stopPropagation|preventDefault={() => activeMenu = activeMenu === video.video_id ? '' : video.video_id}>
                                    Actions ▾
                                </button>
                                {#if activeMenu === video.video_id}
                                <div class="actions-menu" role="menu" on:click|stopPropagation>
                                    <button class="menu-item" role="menuitem" on:click={(e) => retriggerStage(e, video.video_id)}>Re-trigger Stage</button>
                                    <button class="menu-item reprocess" role="menuitem" on:click={(e) => confirmAndReprocess(e, video.video_id, video.video_url)}>Reprocess All</button>
                                </div>
                                {/if}
                            </div>
                        </div>
                    </div>
                </a>
            {/each}
        </div>
    {/if}
</div>

<style>
    .dashboard-container {
        max-width: 1400px;
        min-height: 90vh;
        margin: 0 auto;
        padding: clamp(1rem, 5vw, 2.5rem); /* ✅ fluid padding */
        font-family: 'Inter', sans-serif;
        background-color: #ffffff;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
    }

    h1 {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #1e293b;
    }

    p {
        font-size: 1.1rem;
        color: #64748b;
        margin-bottom: 2rem;
    }

    .videos-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1.5rem;
    }

    .video-card {
        background-color: white;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
        display: flex;
        flex-direction: column;
        text-decoration: none; /* Reset link styles for the card */
        color: inherit; /* Make card text use the default color */
    }

    .video-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);
    }
    
    .card-thumbnail {
        position: relative;
    }

    .card-thumbnail img {
        width: 100%;
        height: auto;
        display: block;
    }

    .card-status {
        position: absolute;
        top: 0.75rem;
        right: 0.75rem;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
        text-transform: capitalize;
    }

    .status-success { background-color: #16a34a; }
    .status-failed { background-color: #dc2626; }
    .status-in-progress { background-color: #f59e0b; }
    .status-unknown { background-color: #64748b; }

    .card-content {
        padding: 1rem;
        flex-grow: 1;
    }

    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0;
        color: #1e293b;
    }

    .card-hook {
        font-size: 0.9rem;
        color: #64748b;
        margin-top: 0.5rem;
        line-height: 1.5;
    }
    
    .card-footer {
        padding: 0.75rem;
        background-color: #f8fafc;
        border-top: 1px solid #e2e8f0;
    }

    .footer-thumbnails {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }

    .footer-thumbnail {
        width: 25%;
        padding-top: 25%;
        background-size: cover;
        background-position: center;
        border-radius: 0.375rem;
    }

    .footer-thumbnail-placeholder {
        width: 25%;
        padding-top: 25%;
        background-color: #e2e8f0;
        border-radius: 0.375rem;
    }

    .footer-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
    }

    .processed-date {
        font-size: 0.8rem;
        color: #64748b;
    }
    
    .actions-menu-container {
        position: relative;
    }

    .actions-button {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        color: #475569;
        padding: 0.3rem 0.8rem;
        font-size: 0.8rem;
        border-radius: 0.375rem;
        cursor: pointer;
    }
    .actions-button:hover {
        background: #e2e8f0;
    }

    .actions-menu {
        position: absolute;
        bottom: 100%; /* Position above the button */
        right: 0;
        background-color: white;
        border-radius: 0.375rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
        z-index: 10;
        width: 150px;
        overflow: hidden;
    }
    
    .menu-item {
        display: block;
        width: 100%;
        text-align: left;
        padding: 0.75rem 1rem;
        background: none;
        border: none;
        cursor: pointer;
        font-size: 0.9rem;
        color:#475569;
    }

    .menu-item:hover {
        background-color: #f8fafc;
    }

    .menu-item.reprocess {
        color: #b91c1c;
    }
    .menu-item.reprocess:hover {
        background-color: #fee2e2;
    }
</style> 