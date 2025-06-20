<div class="flow-container">
    <header>
      <h1>Agent-Based Creative Workflow</h1>
      <p>
        This diagram illustrates the autonomous agent workflow that powers ChannelFlow, 
        transforming a single video into a comprehensive marketing campaign.
      </p>
    </header>
  
    <div class="workflow-diagram">
      <div class="agent-group">
        <div class="agent-node ingestion">Ingestion Agent</div>
        <div class="arrow">↓</div>
        <div class="agent-node transcription">Transcription Agent</div>
        <div class="arrow">↓</div>
        <div class="agent-node analysis">Analysis Agent</div>
      </div>
      
      <div class="parallel-branch">
        <div class="arrow-junction">↓</div>
        <div class="parallel-agents">
          <div class="agent-node copywriting">Copywriting Agent</div>
          <div class="agent-node visuals">Visuals Agent</div>
        </div>
        <div class="arrow-junction">↓</div>
      </div>
  
      <div class="agent-node publisher">Publishing Agent</div>
    </div>
  </div>
  
  <style>
    .flow-container {
        max-width: 1200px;
        margin: 2rem auto;
        padding: 2.5rem;
        font-family: 'Inter', sans-serif;
        background-color: #ffffff;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
        text-align: center;
    }

    header {
        margin-bottom: 3rem;
    }

    header h1 {
        font-size: 2.5rem;
        font-weight: 800;
        color: var(--primary-color);
        margin-bottom: 0.5rem;
    }

    header p {
        font-size: 1.1rem;
        color: #64748b;
        max-width: 700px;
        margin: 0 auto;
    }

    .workflow-diagram {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
    }

    .agent-node {
        padding: 1.25rem 2.5rem;
        border-radius: 0.5rem;
        font-weight: 600;
        font-size: 1.1rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        min-width: 280px;
    }
    
    .arrow {
        font-size: 2rem;
        color: #9ca3af;
        font-weight: 200;
    }

    .parallel-branch {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 100%;
    }

    .parallel-agents {
        display: flex;
        justify-content: center;
        gap: 5rem;
        width: 100%;
        margin: 1rem 0;
    }

    /* Agent specific colors */
    .ingestion { background-color: #3b82f6; }
    .transcription { background-color: #22c55e; }
    .analysis { background-color: #f97316; }
    .copywriting { background-color: #8b5cf6; }
    .visuals { background-color: #ec4899; }
    .publisher { background-color: #64748b; }
  </style> 