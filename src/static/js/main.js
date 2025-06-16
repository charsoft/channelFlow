const ingestForm = document.getElementById('ingestForm');
const urlInput = document.getElementById('youtubeUrl');
const statusDiv = document.getElementById('status');
const progressContainer = document.getElementById('progress-container');
const mainContainer = document.querySelector('.main-container');
const amplifyButton = ingestForm.querySelector('button');
const buttonText = amplifyButton.querySelector('.button-text');
const backButton = document.getElementById('back-to-workflow');

let currentVideoId = null;
let eventSource = null; // To hold the EventSource connection
let isResumableWorkflow = false; // Flag to maintain the "resume" UI state

urlInput.addEventListener('input', () => {
    // Enable button only if there is text in the input field
    amplifyButton.disabled = urlInput.value.trim() === '';
});

document.addEventListener('DOMContentLoaded', () => {
    const reprocessUrl = localStorage.getItem('reprocessUrl');
    if (reprocessUrl) {
        urlInput.value = reprocessUrl;
        amplifyButton.disabled = false;
        statusDiv.textContent = 'URL loaded for reprocessing. Click Amplify to start.';
        // Clear the item so it doesn't load again on next visit
        localStorage.removeItem('reprocessUrl');
    }

    const hamburger = document.querySelector('.hamburger-menu');
    const navLinks = document.querySelector('.nav-links');

    hamburger.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });
});

const statusOrder = [
    "ingested",
    "re-triggering transcription",
    "transcribing",
    "transcribed",
    "re-triggering analysis",
    "analyzing",
    "analyzed",
    "re-triggering copywriting",
    "generating_copy",
    "copy_generated",
    "re-triggering visuals",
    "generating_visuals",
    "visuals_generated",
    "publishing",
    "ready_for_review",
    "published"
];

backButton.addEventListener('click', () => {
    mainContainer.classList.remove('results-view');
});

function setButtonLoading(isLoading) {
    if (isLoading) {
        amplifyButton.disabled = true;
        amplifyButton.classList.add('loading');
    } else {
        amplifyButton.classList.remove('loading');
        // Re-evaluate disabled state based on input content
        amplifyButton.disabled = urlInput.value.trim() === '';
    }
}

function startListening(videoId) {
    if (eventSource) {
        eventSource.close();
    }

    console.log(`[SSE] Connecting to stream for video ID: ${videoId}`);
    eventSource = new EventSource(`/stream-status/${videoId}`);

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('[SSE] Received data:', data);

        // Ignore keep-alive messages
        if (data.status === 'keep-alive') {
            return;
        }
        
        // When we get a real update, we pass it to the same UI function
        updateUI(data); 
    };

    eventSource.onerror = function(err) {
        console.error('[SSE] EventSource failed:', err);
        statusDiv.textContent = 'Connection to server lost. Please refresh.';
        statusDiv.classList.add('status-error');
        eventSource.close();
    };
}

ingestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = urlInput.value;
    if (!url) {
        Swal.fire({ icon: 'error', title: 'Oops...', text: 'Please enter a YouTube URL.' });
        return;
    }

    // YouTube URL Validation
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    if (!youtubeRegex.test(url)) {
        Swal.fire({
            icon: 'error',
            title: 'Invalid URL',
            text: 'Please enter a valid YouTube video URL (e.g., youtube.com/watch?v=... or youtu.be/...).'
        });
        return;
    }

    statusDiv.textContent = 'Checking video status...';
    statusDiv.className = '';
    isResumableWorkflow = false; // Reset state on new submission
    mainContainer.classList.remove('results-view');
    resetAgentUI();
    setButtonLoading(true);

    try {
        // First, check if the video exists without forcing
        const response = await fetch('/api/ingest-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, force: false }),
        });

        const data = await response.json();

        if (response.status === 200 && data.status === 'exists') {
            // Video exists, show the modal
            currentVideoId = data.data.video_id;
            Swal.fire({
                title: 'Video Already Processed',
                text: "This video already exists. What would you like to do?",
                icon: 'question',
                showDenyButton: true,
                showCancelButton: true,
                confirmButtonText: 'Restart from Scratch',
                denyButtonText: 'View & Resume',
                cancelButtonText: 'Never Mind',
                confirmButtonColor: '#DC2626',
                denyButtonColor: '#4F46E5',
            }).then((result) => {
                if (result.isConfirmed) {
                    // "Restart from Scratch" - show second confirmation
                    Swal.fire({
                        title: 'Are you absolutely sure?',
                        text: "This will permanently delete all existing data (including generated copy and images) and re-process the video from the beginning. This cannot be undone.",
                        icon: 'warning',
                        showCancelButton: true,
                        confirmButtonText: 'Yes, delete everything!',
                        cancelButtonText: 'Cancel',
                        confirmButtonColor: '#DC2626',
                        cancelButtonColor: '#64748B'
                    }).then((confirmationResult) => {
                        if (confirmationResult.isConfirmed) {
                            isResumableWorkflow = true; // Set the resume state to true
                            statusDiv.innerHTML = `
                        Existing workflow loaded. Click a stage to re-trigger or 
                        <a href="/video/${currentVideoId}" class="status-link" target="_blank">View Dashboard</a>.
                    `;
                            updateUI(data.data); // Update the UI once with the current state
                            startListening(currentVideoId); // Start listening in case the user re-triggers
                            sendIngestRequest(url, true);
                        } else {
                            setButtonLoading(false); // User cancelled the deletion
                        }
                    });
                } else if (result.isDenied) {
                    // "View & Resume"
                    isResumableWorkflow = true; // Set the resume state to true
                    statusDiv.innerHTML = `
                        Existing workflow loaded. Click a stage to re-trigger or 
                        <a href="/video/${currentVideoId}" class="status-link" target="_blank">View Dashboard</a>.
                    `;
                    updateUI(data.data); // Update the UI once with the current state
                    startListening(currentVideoId); // Start listening in case the user re-triggers
                    setButtonLoading(false);
                } else {
                    // User cancelled the initial modal
                    setButtonLoading(false);
                }
            });
        } else if (response.status === 202) {
            // New video, start listening
            currentVideoId = data.video_id;
            statusDiv.textContent = `Processing video ID: ${currentVideoId}. Waiting for updates...`;
            statusDiv.classList.add('status-success');
            startListening(currentVideoId);
            setButtonLoading(false);
        } else {
            setButtonLoading(false);
            throw new Error(data.message || 'An unknown error occurred');
        }
    } catch (error) {
        setButtonLoading(false);
        statusDiv.textContent = 'An unexpected error occurred.';
        statusDiv.classList.add('status-error');
        Swal.fire({ icon: 'error', title: 'Error', text: 'Could not connect to the server.' });
    }
});

async function sendIngestRequest(url, force) {
    statusDiv.textContent = 'Restarting workflow from scratch...';
    try {
        const response = await fetch('/api/ingest-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, force }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message);
        
        currentVideoId = data.video_id;
        statusDiv.textContent = `Processing video ID: ${currentVideoId}. Waiting for updates...`;
        startListening(currentVideoId);
    } catch(error) {
        statusDiv.textContent = `Error: ${error.message}`;
        statusDiv.classList.add('status-error');
    } finally {
        setButtonLoading(false);
    }
}

function resetAgentUI() {
    document.querySelectorAll('.workflow .agent').forEach(agentEl => {
        agentEl.className = 'agent';
        const arrowEl = agentEl.nextElementSibling;
        if (arrowEl && arrowEl.classList.contains('arrow')) {
            arrowEl.className = 'arrow';
        }
        // Remove old event listeners
        agentEl.replaceWith(agentEl.cloneNode(true));
    });
}

function updateUI(data) {
    // When resuming, the data might be wrapped in a 'data' object.
    const jobData = data.data ? data.data : data;
    console.log('[updateUI] Received data:', JSON.stringify(jobData, null, 2));
    const currentStatus = jobData.status;
    statusDiv.textContent = `Current status: ${currentStatus.replace(/_/g, ' ')}`;
    
    // --- Progress Bar Logic ---
    if (currentStatus === 'transcribing') {
        progressContainer.style.display = 'block';
    } else {
        progressContainer.style.display = 'none';
    }

    resetAgentUI();

    const isTerminalState = jobData.status === 'ready_for_review' || jobData.status === 'published';

    // Only switch to the 'results view' if we are NOT in the middle of a resume flow.
    // The resume flow needs to keep the workflow diagram visible for re-triggering.
    if (isTerminalState && !isResumableWorkflow) {
        mainContainer.classList.add('results-view');
    }

    console.log(`[updateUI] Current Status: ${currentStatus}`);

    const isFailure = currentStatus.includes('failed');
    const baseStatus = currentStatus.replace('_failed', '');
    const currentStatusIndex = statusOrder.indexOf(baseStatus);
    
    const completedStatuses = ["ingested", "transcribed", "analyzed", "copy_generated", "visuals_generated", "ready_for_review", "published"];

    if (currentStatusIndex === -1) {
        console.error(`[updateUI] Status "${baseStatus}" not found in statusOrder array. UI will not update.`);
        return;
    }

    // This maps the status index to the visual agent index in the DOM
    const statusIndexToAgentIndex = (sIndex) => {
        if (sIndex <= 1) return 0; // ingested, re-triggering transcription
        if (sIndex <= 3) return 1;  // transcribing, transcribed
        if (sIndex <= 5) return 2;  // re-triggering analysis, analyzing, analyzed
        if (sIndex <= 8) return 3;  // re-triggering copywriting, generating_copy, copy_generated
        if (sIndex <= 11) return 4;  // re-triggering visuals, generating_visuals, visuals_generated
        return 5;                   // publishing, ready_for_review, published
    };

    const currentAgentIndex = statusIndexToAgentIndex(currentStatusIndex);

    document.querySelectorAll('.workflow .agent').forEach((agentEl, index) => {
        const arrowEl = agentEl.previousElementSibling;

        if (index < currentAgentIndex) {
            // Stage is fully complete and successful
            agentEl.classList.add('success');
            if(arrowEl && arrowEl.classList.contains('arrow')) arrowEl.classList.add('active');
        } else if (index === currentAgentIndex) {
            const isCompleted = completedStatuses.includes(baseStatus);
            // This is the current stage
            if (isFailure) {
                agentEl.classList.add('failed');
            } else if (isCompleted) {
                // This is a "completed" status (transcribed, analyzed...)
                agentEl.classList.add('success');
                if (currentStatus === 'ready_for_review' || currentStatus === 'published') {
                    document.querySelectorAll('.arrow').forEach(a => a.classList.add('active'));
                }
            } else {
                 // This is an "in-progress" status (transcribing, analyzing...)
                agentEl.classList.add('active');
            }
            if(arrowEl && arrowEl.classList.contains('arrow')) arrowEl.classList.add('active');
        } else {
            // This stage has not been reached yet
        }
    });
    
    // The isTerminalState logic was moved up to handle the results-view class

    // Always enable re-triggering if the user is in the resume flow, a stage has failed, or the workflow is complete.
    if (isResumableWorkflow || jobData.status.includes('failed') || isTerminalState) {
        document.querySelectorAll('.agent.success, .agent.failed').forEach(el => {
            el.classList.add('clickable');
            el.addEventListener('click', () => handleStageClick(jobData.video_id, el.id));
        });

        // Special handling for the "Ready for Review" button to act as a link
        const publishingAgentEl = document.getElementById('publishing_agent');
        if (publishingAgentEl && (jobData.status === 'ready_for_review' || jobData.status === 'published')) {
            publishingAgentEl.classList.add('clickable'); // Ensure it looks clickable
            publishingAgentEl.addEventListener('click', () => {
                window.location.href = `/video/${jobData.video_id}`;
            });
        }
    }

    // Always update the results dashboard if it's visible.
    // This handles cases where a user re-triggers a stage from the results view.
    if (mainContainer.classList.contains('results-view')) {
        // The results are now on a separate page, but we can redirect the user there.
        // Or simply let the status update, and the user can navigate.
        // For now, we'll just ensure the final status text provides a clear link.
    }
    
    if (isTerminalState && !isResumableWorkflow) {
        statusDiv.innerHTML = `
            Workflow complete. <a href="/video/${jobData.video_id}" class="status-link">View Results</a>
        `;
    }
}

async function handleStageClick(videoId, agentId) {
    console.log(`Re-triggering ${agentId} for video ${videoId}`);
    const agentIdToStage = {
        "ingestion_agent": "transcription",
        "transcription_agent": "transcription",
        "analysis_agent": "analysis",
        "copywriting_agent": "copywriting",
        "visuals_agent": "visuals"
    };

    const backendStage = agentIdToStage[agentId];
    if (!backendStage) {
        Swal.fire('Cannot Re-trigger', 'This stage cannot be re-triggered from the UI.', 'info');
        return;
    }
    
    statusDiv.textContent = `Re-triggering stage: ${backendStage}...`;
    try {
        const response = await fetch('/api/re-trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: videoId, stage: backendStage }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message);

        statusDiv.textContent = 'Workflow re-triggered! Waiting for updates...';
        // No need to start polling/listening here, the connection is already active

    } catch(error) {
        statusDiv.textContent = `Error: ${error.message}`;
        statusDiv.classList.add('status-error');
    }
} 