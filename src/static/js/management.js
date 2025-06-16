document.addEventListener('DOMContentLoaded', () => {
    const videosGrid = document.getElementById('videos-grid');
    const modal = document.getElementById('video-modal');
    const modalBody = document.getElementById('modal-body');
    const closeModal = document.getElementById('modal-close');
    const hamburger = document.querySelector('.hamburger-menu');
    const navLinks = document.querySelector('.nav-links');

    hamburger.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });

    // --- Data Fetching ---
    async function loadVideos() {
        try {
            const response = await fetch('/api/videos');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            displayVideos(data.videos);
        } catch (error) {
            videosGrid.innerHTML = '<p class="error-message">Could not load video data. Please try again later.</p>';
            console.error('Failed to load videos:', error);
        }
    }

    // --- UI Rendering ---
    function displayVideos(videos) {
        if (!videos || videos.length === 0) {
            videosGrid.innerHTML = '<p>No processed videos found.</p>';
            return;
        }

        videosGrid.innerHTML = ''; // Clear previous content
        videos.forEach(video => {
            const card = document.createElement('div');
            card.className = 'video-card';
            card.dataset.videoId = video.video_id;

            const hook = getHook(video);
            const statusClass = getStatusClass(video.status);
            const imageThumbnails = getImageThumbnails(video);

            let processedDate = 'Not available';
            if (video.received_at) {
                processedDate = new Date(video.received_at).toLocaleDateString();
            }

            card.innerHTML = `
                <div class="card-thumbnail">
                    <img src="https://img.youtube.com/vi/${video.video_id}/hqdefault.jpg" alt="Video thumbnail">
                    <span class="card-status ${statusClass}">${video.status.replace(/_/g, ' ')}</span>
                </div>
                <div class="card-content">
                    <h3 class="card-title">${video.video_title || 'Untitled Video'}</h3>
                    <p class="card-hook">${hook}</p>
                </div>
                <div class="card-footer">
                    <div class="footer-images">${imageThumbnails}</div>
                    <div class="footer-meta">
                        <span class="processed-date">Processed: ${processedDate}</span>
                        <button class="reprocess-button">Reprocess</button>
                    </div>
                </div>
            `;

            card.querySelector('.reprocess-button').addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent the card's click event from firing
                confirmAndReprocess(video.video_id, video.video_url);
            });

            card.addEventListener('click', () => {
                window.location.href = `/video/${video.video_id}`;
            });
            videosGrid.appendChild(card);
        });
    }

    function getImageThumbnails(video) {
        const thumbnails = video.generated_thumbnails || [];
        if (thumbnails.length === 0) {
            return '<span class="no-images">No images generated</span>';
        }
        // Show up to 4 thumbnails
        return thumbnails.slice(0, 4).map(item => 
            `<img src="${item.image_url}" alt="Generated thumbnail" class="footer-thumbnail">`
        ).join('');
    }

    function getHook(video) {
        if (video.substack_hook) {
            return video.substack_hook;
        }
        if (video.structured_data && video.structured_data.summary) {
            // Fallback to the first 100 characters of the summary
            return video.structured_data.summary.substring(0, 100) + '...';
        }
        return 'No hook or summary available.';
    }

    function getStatusClass(status) {
        if (status.includes('failed')) return 'status-failed';
        if (status === 'ready_for_review' || status === 'published') return 'status-success';
        if (status) return 'status-in-progress';
        return 'status-unknown';
    }

    // --- Modal Handling ---
    function openVideoModal(video) {
        modal.style.display = 'flex';
        // TODO: Build a beautiful modal view
        modalBody.innerHTML = `<h2>${video.video_title}</h2><pre>${JSON.stringify(video, null, 2)}</pre>`;
    }

    closeModal.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    // --- Reprocessing Logic ---
    function confirmAndReprocess(videoId, videoUrl) {
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
                reprocessVideo(videoId, videoUrl);
            }
        });
    }

    async function reprocessVideo(videoId, videoUrl) {
        // Instead of calling the API here, we will save the URL to local storage
        // and redirect the user to the main page to start the process themselves.
        localStorage.setItem('reprocessUrl', videoUrl);
        window.location.href = '/';
    }

    function displayQuoteVisuals(videoData) {
        const quotesContainer = document.getElementById('quotes-container');
        const quoteVisuals = videoData.quote_visuals || [];
        quotesContainer.innerHTML = ''; // Clear previous quotes

        if (quoteVisuals.length > 0) {
            quotesContainer.parentElement.style.display = 'block';
            quoteVisuals.forEach(item => {
                const card = document.createElement('div');
                card.className = 'quote-card';
                card.style.backgroundImage = `url('${item.image_url}')`;

                const text = document.createElement('blockquote');
                text.textContent = `"${item.quote}"`;
                
                card.appendChild(text);
                quotesContainer.appendChild(card);
            });
        } else {
            // Hide the entire "Meaningful Quotes" section if there are none
            quotesContainer.parentElement.style.display = 'none';
        }
    }

    function showVideoDetails(videoData) {
        const detailView = document.getElementById('detail-view');
        const videoGrid = document.getElementById('video-grid');
        // ... existing code ...
        
        // Populate and display shorts candidates
        displayShortsCandidates(videoData);

        // Populate and display the new quote visuals
        displayQuoteVisuals(videoData);

        detailView.style.display = 'block';
        videoGrid.style.display = 'none';
    }

    // --- Initial Load ---
    loadVideos();
    
    // Setup manual cleanup button
    const cleanupBtn = document.getElementById('cleanup-cache-btn');
    if (cleanupBtn) {
        cleanupBtn.addEventListener('click', async () => {
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
                        Swal.fire(
                            'Cleaned!',
                            data.message,
                            'success'
                        );
                    } else {
                        throw new Error(data.message || 'Failed to clean up cache.');
                    }
                } catch (error) {
                    console.error('Cleanup error:', error);
                    Swal.fire(
                        'Error!',
                        `An error occurred: ${error.message}`,
                        'error'
                    );
                }
            }
        });
    }
}); 