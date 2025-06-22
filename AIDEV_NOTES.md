Core User Journeys
- Ingestion Flow
    - A user pastes a youtube video url on the Home Page (frontend/routes/src/Home.svelte)
    - If the video is new, then the ingestion agent should connect to YouTube and attempt to download the video into the Videos GCS location
         - If the youtube service returns anything but data, the user is shown a message to "Manually upload their youtube video using the maintenance  page". The system should explain how, in demo mode, the youtube server seem suspicious of so many calls to the service.
    - After the upload has finished, the user is automatically redirected to the Home page so that they can see the progress of their video ingestion. 
        - this means that the on-screen workflow statuses will reflect the current stage, allowing restarting of the process at any point
    - If the video is not new, then the ingestion agent looks for the data file in the video folder, and if found, will immediately light up the workflow with buttons automatically reflected each agent. Any agent that has successfully completed its work will be rerunnable.
    - The workflow that appears on the home page also shows details of everything happening, via a connection with the SSE server.

- Video Dashboard
    - each video that the logged-in user has uploaded will show here, in descending order of upload
    - the thumbnails at the bottom of each video card should come from the collection of generated images stored in Firestore.
    - the actions button should allow the user to reprocess the video. If the user clicks "reprocess", then immediately, the user should navigate to the home page, where the youtube link will automatically populate the textbox, and the user should be told to click the submit button.
       - at this point the usual functionality will ensue. The workflow will notice that the video exists, and will then light ujp, offering them the option to restart any stage, similar typical flow.


Imagen Models as of today:
 -imagen-3.0-generate-002
-imagen-3.0-generate-001
-imagen-3.0-fast-generate-001
-imagegeneration@006
-imagegeneration@005
-imagegeneration@002

