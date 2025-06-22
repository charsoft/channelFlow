<script lang="ts">
  export let showTitle = true;
</script>

<div class="intro-section">
  <div class="intro-content">
      <h2>Meet your agents.</h2>
      <p>
          Our system is designed to take that single video source and propagate its message intelligently across all your digital 'channels.' Our branding reflects this: 'From Source to Stream,' visualizing a single flow branching into multiple, wider rivers of content.
      </p>
  </div>
  <div class="intro-image">
      <img src="/agent-development-kit.png" alt="ChannelFlow Agent Mascot" />
      <p class="image-caption">Powered by Google ADK and Optimized by Google Cloud.</p>
  </div>
</div>

<div class="flow-container">
    {#if showTitle}
      <header>
          <h1>Agent Processing Workflow</h1>
          <p>This page outlines the step-by-step process our AI agents follow to transform a video URL into a complete set of marketing assets.</p>
          <a href="#/dashboard" class="button-secondary">← Back to Dashboard</a>
      </header>
    {/if}

    <div class="workflow">
        
        <div class="flow-step">
            <div class="step-icon">⬇️</div>
            <div class="step-content">
                <h3>1. Ingestion</h3>
                <p class="description">The process starts when a new YouTube URL is submitted. The system fetches basic video details like the title and saves the initial record.</p>
                <div class="details">
                    <strong>Agent:</strong> Ingestion Agent (Implicit)
                    <br/>
                    <strong>Triggers:</strong> `NewVideoDetected` event
                </div>
            </div>
        </div>

        <div class="dependency-arrow">↓</div>

        <div class="flow-step">
            <div class="step-icon">🎙️</div>
            <div class="step-content">
                <h3>2. Transcription</h3>
                <p class="description">The video's audio is transcribed to create a full text version. This transcript is the foundation for all subsequent analysis.</p>
                <div class="details">
                    <strong>Agent:</strong> Transcription Agent
                    <br/>
                    <strong>Depends On:</strong> Ingestion
                    <br/>
                    <strong>Triggers:</strong> `TranscriptReady` event
                </div>
            </div>
        </div>

        <div class="dependency-arrow">↓</div>

        <div class="flow-step">
            <div class="step-icon">🧠</div>
            <div class="step-content">
                <h3>3. Content Analysis</h3>
                <p class="description">The transcript is analyzed to extract key topics, identify potential "shorts" candidates, and create a structured summary of the content.</p>
                 <div class="details">
                    <strong>Agent:</strong> Analysis Agent
                    <br/>
                    <strong>Depends On:</strong> Transcription
                    <br/>
                    <strong>Triggers:</strong> `ContentAnalysisComplete` event
                </div>
            </div>
        </div>

        <div class="dependency-arrow">↓</div>

        <div class="flow-step">
            <div class="step-icon">✍️</div>
            <div class="step-content">
                <h3>4. Copywriting</h3>
                <p class="description">Using the analysis and transcript, this agent generates various marketing materials, such as social media posts, email newsletters, and articles.</p>
                <div class="details">
                    <strong>Agent:</strong> Copywriter Agent
                    <br/>
                    <strong>Depends On:</strong> Content Analysis
                    <br/>
                    <strong>Triggers:</strong> `CopyReady` event
                </div>
            </div>
        </div>
        
        <div class="dependency-arrow">↓</div>

        <div class="flow-step">
            <div class="step-icon">🎨</div>
            <div class="step-content">
                <h3>5. Visuals Generation</h3>
                <p class="description">Based on the marketing copy and content analysis, this agent generates relevant visual assets, like thumbnails and quote graphics.</p>
                <div class="details">
                    <strong>Agent:</strong> Visuals Agent
                    <br/>
                    <strong>Depends On:</strong> Copywriting
                    <br/>
                    <strong>Triggers:</strong> `VisualsReady` event (marks completion)
                </div>
            </div>
        </div>

    </div>
</div>

<style>
    .intro-section {
      display: flex;
      align-items: center;
      gap: 2rem;
      background-color: var(--background-color-light);
      padding: 3rem 2rem;
      border-radius: 0.75rem;
      max-width: 900px;
      margin: 2rem auto;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
      border: 1px solid var(--border-color);
    }
    .intro-content {
      flex: 2;
    }
    .intro-content h2 {
      font-size: 2rem;
      font-weight: 800;
      color: #1e293b;
      margin-bottom: 1rem;
    }
    .intro-content p {
      font-size: 1rem;
      color: #4b5563;
      line-height: 1.6;
    }
    .intro-image {
      flex: 1;
      max-width: 250px;
      text-align: center;
    }
    .intro-image img {
      width: 100%;
      height: auto;
      border-radius: 0.5rem;
    }
    .image-caption {
      font-size: 0.8rem;
      font-style: italic;
      color: #64748b;
      margin-top: 1rem;
    }

    .flow-container {
        max-width: 900px;
        margin: 0 auto;
        min-height: 90vh;
        padding: 2rem;
        font-family: 'Inter', sans-serif;
        background-color: #fff;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
    }
    
    header {
        text-align: center;
        margin-bottom: 3rem;
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 2rem;
    }

    header h1 {
        font-size: 2.25rem;
        font-weight: 800;
        color: #1e293b;
    }
    
    header p {
        font-size: 1.1rem;
        color: #64748b;
        max-width: 650px;
        margin: 0.5rem auto 1.5rem auto;
    }
    
    .workflow {
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    .flow-step {
        display: flex;
        align-items: flex-start;
        gap: 1.5rem;
        width: 100%;
        padding: 1.5rem;
        border: 1px solid transparent;
    }
    
    .step-icon {
        font-size: 2.5rem;
    }

    .step-content h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.5rem;
        font-weight: 700;
        color: #374151;
    }
    
    .step-content .description {
        font-size: 1rem;
        color: #4b5563;
        line-height: 1.6;
        margin-bottom: 1rem;
    }

    .step-content .details {
        font-size: 0.9rem;
        color: #6b7280;
        background-color: #f8fafc;
        padding: 0.75rem 1rem;
        border-radius: 0.375rem;
        border: 1px solid #e5e7eb;
    }

    .dependency-arrow {
        font-size: 1.5rem;
        color: #d1d5db;
        margin: 0.5rem 0;
    }

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
</style> 