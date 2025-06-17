<script lang="ts">
  import { onMount } from 'svelte';
  import { initializeApp, type FirebaseApp } from 'firebase/app';
  import { 
    getAuth, 
    onAuthStateChanged, 
    GoogleAuthProvider, 
    signInWithPopup,
    type Auth
  } from 'firebase/auth';
  import Swal from 'sweetalert2';

  // --- App State ---
  let youtubeUrl: string = '';
  let authButtonText: string = 'Sign in with Google';
  let userDisplayName: string = '';
  let isIngesting: boolean = false;
  let currentStatus: string = '';
  let activeAgent: string = '';
  let idToken: string | null = null;
  let currentVideoId: string | null = null;
  let eventSource: EventSource | null = null;
  
  // Firebase state
  let auth: Auth;

  // States for results view
  let showResults: boolean = false;

  // Agent names for the workflow UI
  const agents = ['Ingestion', 'Transcription', 'Analysis', 'Copywriter', 'Visuals', 'Publisher'];

  onMount(async () => {
    try {
      const response = await fetch('/api/config');
      if (!response.ok) {
        throw new Error(`Failed to fetch config: ${response.statusText}`);
      }
      const config = await response.json();

      const firebaseConfig = {
        apiKey: config.firebase_api_key,
        authDomain: config.firebase_auth_domain,
        projectId: config.firebase_project_id
      };
      
      const app: FirebaseApp = initializeApp(firebaseConfig);
      auth = getAuth(app);

      onAuthStateChanged(auth, user => {
        if (user) {
          user.getIdToken().then(token => {
            idToken = token;
            userDisplayName = user.displayName || 'User';
            authButtonText = 'Sign Out';
          });
        } else {
          idToken = null;
          userDisplayName = '';
          authButtonText = 'Sign in with Google';
        }
      });

    } catch (error) {
      console.error('Failed to initialize app:', error);
      Swal.fire({
        icon: 'error',
        title: 'Initialization Failed',
        text: 'Could not connect to the server. Please try again later.',
      });
    }
  });

  function handleAuthClick() {
    if (!auth) {
        Swal.fire('Error', 'Authentication service is not ready.', 'error');
        return;
    }
    if (auth.currentUser) {
      auth.signOut();
    } else {
      const provider = new GoogleAuthProvider();
      provider.addScope('https://www.googleapis.com/auth/youtube.readonly');
      signInWithPopup(auth, provider)
        .then((result) => {
          // This gives you a Google Access Token. You can use it to access the Google API.
          const credential = GoogleAuthProvider.credentialFromResult(result);
          const token = credential?.accessToken;
          // The signed-in user info.
          const user = result.user;
          console.log('Successfully signed in with Google', user);
        }).catch((error) => {
          const errorCode = error.code;
          const errorMessage = error.message;
          const email = error.customData?.email;
          const credential = GoogleAuthProvider.credentialFromError(error);
          Swal.fire('Authentication Failed', `Error: ${errorMessage}`, 'error');
        });
    }
  }
  
  async function handleIngestSubmit() {
    if (!idToken) {
        Swal.fire({ icon: 'error', title: 'Not Authenticated', text: 'Please log in first.' });
        return;
    }
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    if (!youtubeRegex.test(youtubeUrl)) {
        Swal.fire({ icon: 'error', title: 'Invalid URL', text: 'Please enter a valid YouTube video URL.' });
        return;
    }

    currentStatus = 'Checking video status...';
    showResults = false;
    resetAgentUI();
    isIngesting = true;

    try {
        const response = await fetch('/api/ingest-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${idToken}` },
            body: JSON.stringify({ url: youtubeUrl, force: false }),
        });
        const data = await response.json();
        if (response.status === 200 && data.status === 'exists') {
            currentVideoId = data.data.video_id;
            const result = await Swal.fire({
                title: 'Video Already Processed',
                text: "This video already exists. What would you like to do?",
                icon: 'question',
                showDenyButton: true, showCancelButton: true,
                confirmButtonText: 'Restart from Scratch', denyButtonText: 'View & Resume',
                confirmButtonColor: '#DC2626', denyButtonColor: '#4F46E5',
            });
            if (result.isConfirmed) {
                await sendIngestRequest(youtubeUrl, true);
            } else if (result.isDenied) {
                window.location.href = `/video/${currentVideoId}`;
            } else {
                isIngesting = false;
            }
        } else if (response.ok) {
            await sendIngestRequest(youtubeUrl, true);
        } else {
            throw new Error(data.detail || 'An unknown error occurred.');
        }
    } catch (error: any) {
        Swal.fire('Error', error.message, 'error');
        isIngesting = false;
    }
  }

  async function sendIngestRequest(url: string, force: boolean) {
    try {
        const response = await fetch('/api/ingest-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${idToken}` },
            body: JSON.stringify({ url, force }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Server error: ${response.status}`);
        currentVideoId = data.video_id;
        currentStatus = 'Workflow started... waiting for events.';
        setupEventSource(currentVideoId);
    } catch (error: any) {
        Swal.fire('Ingestion Error', error.message, 'error');
        isIngesting = false;
    }
  }

  function setupEventSource(videoId: string) {
    if (!idToken) return;
    eventSource = new EventSource(`/api/events/${videoId}?token=${encodeURIComponent(idToken)}`);
    eventSource.onmessage = (event) => {
        const eventData = JSON.parse(event.data);
        updateWorkflowUI(eventData);
    };
    eventSource.onerror = (err) => {
        console.error('EventSource failed:', err);
        currentStatus = 'Connection to server lost. Please refresh.';
        eventSource?.close();
        isIngesting = false;
    };
  }

  function updateWorkflowUI(eventData: any) {
    console.log("Received event:", eventData);
    const agentName = eventData.source;
    activeAgent = agentName;
    currentStatus = `Agent ${agentName} is working...`;
    
    if (agentName === 'Publisher' && eventData.action === 'result') {
        currentStatus = 'Workflow complete!';
        eventSource?.close();
        isIngesting = false;
        showResults = true;
    } else if (eventData.action === 'error') {
        currentStatus = `Agent ${agentName} failed.`;
        eventSource?.close();
        isIngesting = false;
    }
  }
  
  function resetAgentUI() {
    activeAgent = '';
  }

  function handleArtifactClick(agentName: string) {
    if (!currentVideoId) return;
    window.open(`/video/${currentVideoId}?agent=${agentName}`, '_blank');
  }

</script>

<main class="main-container">
  <div class="header-nav">
      <a href="/" class="logo-link">
          <img src="/src/assets/channel-flow-logo.png" alt="ChannelFlow Logo" class="logo-icon">
      </a>
      <div class="nav-links">
        {#if userDisplayName}
          <p>Welcome, {userDisplayName}</p>
        {/if}
        <button class="auth-button" on:click={handleAuthClick}>{authButtonText}</button>
      </div>
  </div>

  <div class="content-column">
    <h1>Amplify Your Message</h1>
    <p>
        Turn any YouTube video into a suite of ready-to-publish social media content.
        Just paste the URL below to get started.
    </p>
    <form on:submit|preventDefault={handleIngestSubmit}>
        <input type="url" bind:value={youtubeUrl} placeholder="https://www.youtube.com/watch?v=..." required />
        <button type="submit" disabled={isIngesting || !youtubeUrl.trim()}>
            <span class="button-text">{isIngesting ? 'Processing...' : 'Amplify'}</span>
        </button>
    </form>
    <div id="status">{currentStatus}</div>
  </div>

  <div class="workflow-column">
      <h2>Live Workflow</h2>
      <div class="workflow">
          {#each agents as agent, i}
              <div class="agent" class:active={activeAgent === agent}>{agent}</div>
              {#if i < agents.length - 1}
                  <div class="arrow" class:active={activeAgent === agent}>↓</div>
              {/if}
          {/each}
      </div>
  </div>

</main>