# channelFlow
Hackathon entry!

Running it Locally:
You still have to set up the OAuth 2.0 client in your GCP project, since this app requires users to authentication with Google Cloud.



Setting it up in GCP

How to set up:
- Create a Google Cloud project
- Manually create the OAuth Client ID and Secret in GCP Console
	- under APIs & Services, click "Credentials"
	- click "Configure Consent Screen", then "Get Started"
 	- enter the app name (whatever you want), your email address, etc.
  	- choose Internal (testing only)
  	- click Finish
  - Now click "Create OAuth Client"
  	- Application Type: Web Application
   	- Name it (internally)
    	- add authorized Javascript Origins
     		- http://localhost:5173  -- for the local frontend 
       		- http://localhost:8000  -- for the local backend
         - click create (we will come back here and add the official frontends when we deploy to cloud run)
  - Copy the Google_Client_Id, paste it in the .env.local and the .env files on the project root
  - Copy the Goole_Client_Secret, paste it in the environment variables as well
  - Paste both values in the terraform.tfvars relative environment fields
  - 
Configure Google OAuth Client: In your Google Cloud Console, under "APIs & Services" -> "Credentials", make sure the OAuth 2.0 Client ID you're using is configured as a "Web application" and, critically, that you've added http://localhost:8000 (for local testing) and your deployed application's URL to the "Authorized JavaScript origins". The redirect_uri is handled by the new Google Identity Services library and doesn't need to be configured for this flow.
- Copy the clientID and Client Secret. Put the values in the terraform.tfvars file.
 
- Clone this repository
- Open the repo in your favorite code editor
- install google cloud sdk
- authenticate to google cloud
- Set your project to the one you just created
- Set up the environment for Python
	- pyenv install 3.12.4
 - Create the virtual environment
 	- python -m venv .venv
- Activate the virtual environment
 	- .\\.venv\\Scripts\\Activate.ps1
- Now install the requirements into the virtual environment	
	- pip install -r requirements.txt
- docker
  - docker build -t channelflow:latest .
  - docker tag channelflow:latest us-central1-docker.pkg.dev/channelflow-test-deploy/channelflow-test-deploy-api-repo/channelflow:latest
  - docker push us-central1-docker.pkg.dev/channelflow-test-deploy/channelflow-test-deploy-api-repo/channelflow:latest
  - (if not using terraform... and you won't every time, go to cloud run and redeploy because we haven't automated it yet) 
 - Run the Terraform files ()
 	- copy terraform-example.tfvars --> terraform.tfvars
    		- secret_key needs to be generated using this command: 
			python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
		- firebase settings can be dound at console.firebase.google.com
  		- oauth 2.0 client id and secrets should be placed here too.
 	- cd terraform
  	- terraform init
--------------------------
BACKEND
--------------------------
deploy to cloud run (this will happen through terraform
 -   	 

 uvicorn src.app:app --reload

FIREBASE
------------
- Go to your Firebase Console: https://console.firebase.google.com/
- Select the correct project (the one matching your .env file keys).
- In the left-hand navigation menu, go to the Authentication section.
- Click on the Settings tab (near the top of the page, next to "Users").
- Select the Authorized domains sub-tab.
- Click the Add domain button.
- Enter localhost in the dialog box and click Add.
   After adding localhost to the list, the Firebase SDK running on your local machine will be recognized, and the authentication flow should proceed without this error. It might take a minute or two for the setting to take effect.
--------------------------
FRONTEND
--------------------------
firebase deploy --only hosting      
