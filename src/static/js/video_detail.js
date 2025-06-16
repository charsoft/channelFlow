document.addEventListener('DOMContentLoaded', () => {
    const detailContent = document.getElementById('video-detail-content');
    const videoId = window.location.pathname.split('/').pop();
    const tabContainer = document.querySelector('.tab-nav');
    const hamburger = document.querySelector('.hamburger-menu');
    const navLinks = document.querySelector('.nav-links');
    let currentVideoData = null; // Variable to hold the loaded video data

    function sanitizeTitleForFilename(title) {
        if (!title) return 'video_clip';
        // Remove characters that are not filename-friendly, replace spaces with underscores.
        const sanitized = title.replace(/[*:"<>?|/\\.]/g, '').replace(/\s+/g, '_').toLowerCase();
        // Truncate to a reasonable length to avoid issues with max filename length.
        return (sanitized.substring(0, 80) || 'video_clip');
    }

    hamburger.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });

    // --- Tab Switching Logic ---
    if (tabContainer) {
        tabContainer.addEventListener('click', (e) => {
            if (e.target.matches('.tab-link')) {
                // Remove active class from all tabs and content
                document.querySelectorAll('.tab-link').forEach(tab => tab.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

                // Add active class to clicked tab and its content
                const tabId = e.target.dataset.tab;
                e.target.classList.add('active');
                document.getElementById(tabId).classList.add('active');
            }
        });
    }

    async function loadVideoDetails() {
        if (!videoId) {
            detailContent.innerHTML = '<p class="error-message">No video ID specified.</p>';
            return;
        }

        const loader = document.getElementById('loader');
        if (loader) loader.style.display = 'block';

        try {
            const response = await fetch(`/api/video/${videoId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            renderVideoDetails(data.video);
        } catch (error) {
            detailContent.innerHTML = '<p class="error-message">Could not load video details. Please try again later.</p>';
            console.error('Failed to load video details:', error);
        } finally {
            if (loader) loader.style.display = 'none';
        }
    }

    function renderVideoDetails(data) {
        currentVideoData = data; // Store data in the module-scoped variable
        // This function no longer needs to manage the loader, it's handled in loadVideoDetails

        // --- Populate Header ---
        document.getElementById('video-title-placeholder').textContent = data.video_title || 'Untitled Video';
        
        const receivedAtDate = data.received_at ? new Date(data.received_at) : null;
        if (receivedAtDate) {
            document.getElementById('video-date').textContent = `Processed: ${receivedAtDate.toLocaleDateString()}`;
        }

        const statusBanner = document.getElementById('video-status-banner');
        statusBanner.textContent = `Status: ${data.status.replace(/_/g, ' ')}`;
        statusBanner.className = `status-banner ${getStatusClass(data.status)}`;

        // --- Embed YouTube Player ---
        if (window.YT) {
            new window.YT.Player('youtube-player', {
                height: '100%',
                width: '100%',
                videoId: data.video_id,
            });
        } else {
            document.getElementById('youtube-player').innerHTML = '<p>YouTube player could not be loaded.</p>';
        }

        // --- Populate Main Details ---
        const summarySection = document.getElementById('summary-section');
        if (data.structured_data && data.structured_data.summary) {
            document.getElementById('video-summary').textContent = data.structured_data.summary;
        } else {
            summarySection.style.display = 'none';
        }
        
        // --- Populate Transcript ---
        const transcriptSection = document.getElementById('transcript-section');
        if (data.transcript_gcs_uri) {
            document.getElementById('transcript-download-link').href = data.transcript_gcs_uri.replace("gs://", "https://storage.googleapis.com/");
            // Fetch and display transcript text
             fetch(data.transcript_gcs_uri.replace("gs://", "https://storage.googleapis.com/"))
                .then(response => response.json())
                .then(transcriptData => {
                     document.getElementById('transcript-content').textContent = transcriptData.full_transcript || 'Transcript text not found in JSON.';
                })
                .catch(err => {
                    console.error("Could not load transcript text:", err);
                    document.getElementById('transcript-content').textContent = "Could not load transcript.";
                });
        } else {
            transcriptSection.style.display = 'none';
        }

        // --- Populate Generated Thumbnails ---
        const thumbnailsContainer = document.getElementById('thumbnails-container');
        const thumbnailsSection = thumbnailsContainer.parentElement;
        const thumbnails = data.generated_thumbnails || [];
        if (thumbnails.length > 0) {
            thumbnailsContainer.innerHTML = thumbnails.map(item =>
                `
                <div class="thumbnail-item">
                    <div class="thumbnail-image-wrapper">
                        <img src="${item.image_url}" alt="Generated visual">
                    </div>
                    <div class="thumbnail-prompt">
                        <h4>Prompt:</h4>
                        <p>${item.prompt}</p>
                        <button class="button-secondary preview-post-btn" data-image-url="${item.image_url}">Preview Post</button>
                    </div>
                </div>
                `
            ).join('');
        } else {
            thumbnailsSection.style.display = 'none';
        }

        // --- Populate Generated Copy ---
        const copyContainer = document.getElementById('copy-assets-container');
        const copySection = copyContainer.parentElement;
        let copyHtml = '';
        if (data.marketing_copy) {
             if (data.marketing_copy.facebook_post) {
                copyHtml += `
                    <div class="copy-asset-card">
                        <h4>Facebook / Instagram Post</h4>
                        <div contenteditable="true" class="copy-text">${data.marketing_copy.facebook_post}</div>
                    </div>`;
            }
             if (data.marketing_copy.email_newsletter) {
                 copyHtml += `
                    <div class="copy-asset-card">
                        <h4>Email Newsletter</h4>
                        <div contenteditable="true" class="copy-text">${data.marketing_copy.email_newsletter}</div>
                    </div>`;
            }
        }
        if(copyHtml) {
            copyContainer.innerHTML = copyHtml;
        } else {
            copySection.style.display = 'none';
        }

        // --- Populate Substack Link ---
        const substackLink = document.getElementById('substack-download-link');
        if (data.substack_gcs_uri) {
            substackLink.href = data.substack_gcs_uri.replace("gs://", "https://storage.googleapis.com/");
        } else {
            substackLink.style.display = 'none';
        }

        // --- Populate Shorts Candidates ---
        const shortsContainer = document.getElementById('shorts-candidates-container');
        const shortsSection = document.getElementById('tab-shorts'); // Changed selector for the whole tab
        const shorts = data.structured_data ? data.structured_data.shorts_candidates : [];
        if (shorts && shorts.length > 0) {
            let content = '<h2>Shorts Candidates</h2><p class="section-description">Potential high-impact shorts identified by the analysis agent. Adjust timings and click "Generate Clip" to create the video.</p>';
            const list = document.createElement('ul');
            list.className = 'shorts-list';
            shorts.forEach((short, index) => {
                const item = document.createElement('li');
                item.className = 'short-candidate-item';
                const startTime = parseFloat(short.start_time).toFixed(1);
                const endTime = parseFloat(short.end_time).toFixed(1);
                const downloadFilename = `${sanitizeTitleForFilename(short.suggested_title)}.mp4`;

                // Conditionally render the actions based on whether a clip is already generated
                const actionContent = short.generated_clip_url
                    ? `
                        <div class="clip-preview-container" id="clip-container-${index}">
                            <video controls src="${short.generated_clip_url}" width="200"></video>
                            <div class="clip-buttons">
                                <a href="${short.generated_clip_url}" download="${downloadFilename}" class="button-secondary">Download</a>
                                <button class="button-danger re-generate-clip-btn" data-index="${index}">Re-generate</button>
                            </div>
                        </div>
                        <div class="inline-loader short-loader" style="display: none;"></div>
                    `
                    : `
                        <button class="button-secondary generate-clip-btn" data-index="${index}">
                            Generate Clip
                        </button>
                        <div class="clip-preview-container" id="clip-container-${index}" style="display: none;"></div>
                        <div class="inline-loader short-loader" style="display: none;"></div>
                    `;

                item.innerHTML = `
                    <div class="short-info">
                        <h4>${short.suggested_title}</h4>
                        <p><strong>Reason:</strong> ${short.reason}</p>
                        <p class="snippet"><em>"${short.transcript_snippet}"</em></p>
                        <div class="timestamp-editor">
                            <label for="start-time-${index}">Start (s):</label>
                            <input type="number" step="0.1" id="start-time-${index}" class="time-input" value="${startTime}">
                            <label for="end-time-${index}">End (s):</label>
                            <input type="number" step="0.1" id="end-time-${index}" class="time-input" value="${endTime}">
                        </div>
                    </div>
                    <div class="short-actions">
                        ${actionContent}
                    </div>
                `;
                list.appendChild(item);
            });
            shortsContainer.innerHTML = content;
            shortsContainer.appendChild(list);
        } else {
            shortsSection.style.display = 'none';
        }

        // --- Populate Quote Visuals ---
        const quotesContainer = document.getElementById('quotes-container');
        const quotesSection = document.getElementById('quotes-section');
        const quoteVisuals = data.quote_visuals || [];
        if (quoteVisuals.length > 0) {
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
            quotesSection.style.display = 'none';
        }
    }

    function getStatusClass(status) {
        if (status.includes('failed')) return 'status-failed';
        if (status === 'ready_for_review' || status === 'published') return 'status-success';
        if (status) return 'status-in-progress';
        return 'status-unknown';
    }
    
    // --- On-Demand Generation Logic ---
    const generatePromptsBtn = document.getElementById('generate-prompts-btn');
    const promptsLoader = document.getElementById('prompts-loader');
    const newPromptsList = document.getElementById('new-prompts-list');

    generatePromptsBtn.addEventListener('click', async () => {
        generatePromptsBtn.disabled = true;
        promptsLoader.style.display = 'block';
        newPromptsList.innerHTML = '';
        
        try {
            const response = await fetch(`/api/video/${videoId}/generate-prompts`, { method: 'POST' });
            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }
            const data = await response.json();
            renderNewPrompts(data.prompts);
        } catch (error) {
            console.error('Failed to generate new prompts:', error);
            newPromptsList.innerHTML = `<li class="error-message">Could not generate prompts.</li>`;
        } finally {
            generatePromptsBtn.disabled = false;
            promptsLoader.style.display = 'none';
        }
    });

    function renderNewPrompts(prompts) {
        if (!prompts || prompts.length === 0) {
            newPromptsList.innerHTML = `<li>No new prompts were generated.</li>`;
            return;
        }
        newPromptsList.innerHTML = prompts.map(prompt => `
            <li>
                <span class="prompt-text">${prompt}</span>
                <button class="button-secondary generate-image-btn" data-prompt="${encodeURIComponent(prompt)}">Generate</button>
            </li>
        `).join('');
    }

    newPromptsList.addEventListener('click', async (e) => {
        if (e.target.matches('.generate-image-btn')) {
            const button = e.target;
            const prompt = decodeURIComponent(button.dataset.prompt);
            
            button.disabled = true;
            button.textContent = 'Generating...';

            try {
                const response = await fetch(`/api/video/${videoId}/generate-thumbnail`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ prompt: prompt })
                });

                if (!response.ok) throw new Error('Failed to generate thumbnail');
                
                const data = await response.json();
                addThumbnailToGrid(data.thumbnail);
                
                // Remove the prompt from the list once used
                button.closest('li').remove();

            } catch (error) {
                console.error("On-demand thumbnail generation failed:", error);
                button.textContent = 'Failed!';
                button.style.backgroundColor = '#E53E3E'; // Red color for failure
            }
        }
    });

    // --- Image Modal Logic ---
    const imageModal = document.getElementById('image-modal');
    const modalImage = imageModal.querySelector('.modal-content-image');
    const closeModal = imageModal.querySelector('.modal-close-button');
    const thumbnailsContainer = document.getElementById('thumbnails-container');

    thumbnailsContainer.addEventListener('click', (e) => {
        if (e.target.tagName === 'IMG') {
            modalImage.src = e.target.src;
            imageModal.style.display = 'flex';
        }
    });

    closeModal.addEventListener('click', () => {
        imageModal.style.display = 'none';
    });

    imageModal.addEventListener('click', (e) => {
        // Close if the overlay (but not the image itself) is clicked
        if (e.target === imageModal) {
            imageModal.style.display = 'none';
        }
    });

    // --- Social Preview Modal ---
    thumbnailsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('preview-post-btn')) {
            const button = e.target;
            const imageUrl = button.dataset.imageUrl;
            
            // Access the module-scoped variable, not the window object
            const facebookPost = currentVideoData?.marketing_copy?.facebook_post;
            
            if (!facebookPost) {
                Swal.fire('Error', 'Could not find post content.', 'error');
                return;
            }
            
            // Convert <br> tags to newlines for clipboard
            const plainTextPost = facebookPost.replace(/<br\s*\/?>/gi, '\n');

            Swal.fire({
                title: 'Post Preview',
                html: `
                    <div class="social-preview-content">
                        <img src="${imageUrl}" alt="Post image preview" style="max-width: 100%; border-radius: 8px;">
                        <div class="social-preview-caption">${facebookPost}</div>
                    </div>
                `,
                confirmButtonText: 'Copy Text & Close',
                showCancelButton: true,
                cancelButtonText: 'Just Close',
                customClass: {
                    popup: 'social-preview-popup'
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    // First, copy the text
                    navigator.clipboard.writeText(plainTextPost).then(() => {
                        // Then, trigger the image download with the video title
                        downloadImage(imageUrl, currentVideoData.video_title);

                        Swal.fire({
                            toast: true,
                            position: 'top-end',
                            icon: 'success',
                            title: 'Copied & Downloading!',
                            showConfirmButton: false,
                            timer: 2000 // A bit longer to notice the download
                        });
                    }).catch(err => {
                        Swal.fire('Error', 'Could not copy text.', 'error');
                    });
                }
            });
        }
    });

    function addThumbnailToGrid(thumbnail) {
        const thumbnailsContainer = document.getElementById('thumbnails-container');
        const newItem = document.createElement('div');
        newItem.className = 'thumbnail-item';
        newItem.innerHTML = `
            <div class="thumbnail-image-wrapper">
                <img src="${thumbnail.image_url}" alt="Generated visual">
            </div>
            <div class="thumbnail-prompt">
                <h4>Prompt:</h4>
                <p>${thumbnail.prompt}</p>
                <button class="button-secondary preview-post-btn" data-image-url="${thumbnail.image_url}">Preview Post</button>
            </div>
        `;
        thumbnailsContainer.appendChild(newItem);
    }

    // --- Load YouTube IFrame API ---
    const tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    window.onYouTubeIframeAPIReady = function() {
        loadVideoDetails();
    };

    // Make copy function available
    window.copyToClipboard = (elementId) => {
        const element = document.getElementById(elementId);
        navigator.clipboard.writeText(element.innerText).then(() => {
            Swal.fire({
                toast: true,
                position: 'top-end',
                icon: 'success',
                title: 'Copied to clipboard!',
                showConfirmButton: false,
                timer: 1500
            });
        });
    }

    async function downloadImage(imageUrl, videoTitle) {
        try {
            // Add { cache: 'no-cache' } to bypass any stale CORS responses from the browser cache.
            const response = await fetch(imageUrl, { cache: 'no-cache' });
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            // Sanitize the title to make it filesystem-friendly and use it in the name
            const safeTitle = videoTitle.replace(/[^a-z0-9]/gi, '_').toLowerCase();
            a.download = `channel_post_${safeTitle}.png`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (err) {
            console.error('Failed to download image:', err);
            Swal.fire('Download Error', 'Could not download the image.', 'error');
        }
    }

    // --- Shorts Clip Generation ---
    const shortsContainer = document.getElementById('shorts-candidates-container');
    shortsContainer.addEventListener('click', async (e) => {
        const isGenerate = e.target.classList.contains('generate-clip-btn');
        const isReGenerate = e.target.classList.contains('re-generate-clip-btn');

        if (isGenerate || isReGenerate) {
            const button = e.target;
            const index = button.dataset.index;
            
            // Get times from the input fields
            const startTime = document.getElementById(`start-time-${index}`).value;
            const endTime = document.getElementById(`end-time-${index}`).value;
            
            const loader = button.closest('.short-actions').querySelector('.short-loader');
            const previewContainer = document.getElementById(`clip-container-${index}`);

            // Show loader and disable button
            loader.style.display = 'block';
            button.style.display = 'none';
            
            if (isReGenerate) {
                // If re-generating, first clear the old video
                 previewContainer.innerHTML = '';
            }

            try {
                const response = await fetch(`/api/video/${videoId}/create-clip`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ start_time: startTime, end_time: endTime, short_index: index })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || 'Failed to generate clip');
                }

                const data = await response.json();
                
                // Get the title for the filename
                const short = currentVideoData.structured_data.shorts_candidates[index];
                const downloadFilename = `${sanitizeTitleForFilename(short.suggested_title)}.mp4`;

                // Display the video
                previewContainer.innerHTML = `
                    <video controls src="${data.clip_url}" width="200"></video>
                    <div class="clip-buttons">
                        <a href="${data.clip_url}" download="${downloadFilename}" class="button-secondary">Download</a>
                        <button class="button-danger re-generate-clip-btn" data-index="${index}">Re-generate</button>
                    </div>
                `;
                previewContainer.style.display = 'block';

            } catch (err) {
                console.error('Failed to generate clip:', err);
                Swal.fire('Clip Generation Error', err.toString(), 'error');
                 // Restore the button if there was an error
                button.style.display = 'block';

            } finally {
                loader.style.display = 'none';
            }
        }
    });
}); 