Core User Journeys
- Ingestion Flow
    - A user pastes a youtube video url on the Home Page (frontend/routes/src/Home.svelte)
    - If the video is new, then the ingestion agent should connect to YouTube and attempt to download the video into the Videos GCS location
         - If the youtube service returns anything but data, the user is shown a message to "Manually upload their youtube video using the maintenance  page". The system should explain how, in demo mode, the youtube server seem suspicious of so many calls to the service.
    - After the upload has finished, the user is automatically redirected to the Home page so that they can see the progress of their video ingestion. 
        - this means that the on-screen workflow statuses will reflect the current stage, allowing restarting of the process at any point
    - If the video is not new, then the ingestion agent looks for the data file in the video folder, and if found, will immediately light up the workflow with buttons automatically reflected each agent. Any agent that has successfully completed its work will be rerunnable.
    - The workflow that appears on the home page also shows details of everything happening, via a connection with the SSE server.
    
    
