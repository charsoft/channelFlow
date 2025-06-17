# channelFlow
Hackathon entry!

Running it Locally:
You still have to set up the OAuth 2.0 client in your GCP project, since this app requires users to authentication with Google Cloud.



Setting it up in GCP

Create a Google Cloud project

- Clone this repo, open it up in your favorite code editor.
	
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
- Create a storage bucket (to be used as terraform backend)
	- copy the name, paste it into the terraform/main.tf somewhere around 17


 -----
Create an artifact repo: 
gcloud artifacts repositories create channelflow-api-repo --project=<YOUR-PROJECT-ID-HERE> --repository-format=docker --location=us-central1 --description="ChannelFlow API Docker repository"n
Create the docker container, and push to your repo
  - cd to the root of the repo first
  - docker build -t channelflow:latest .
  - docker tag channelflow:latest us-central1-docker.pkg.dev/<YOUR-PROJECT-ID-HERE>/channelflow-api-repo/channelflow:latest
  - docker push us-central1-docker.pkg.dev/<YOUR-PROJECT-ID-HERE>/channelflow-api-repo/channelflow:latest
  - (if not using terraform... and you won't every time, go to cloud run and redeploy because we haven't automated it yet) 
 - Run the Terraform files ()
 	- copy terraform-example.tfvars --> terraform.tfvars
    		- secret_key needs to be generated using this command: 
			python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
		- firebase settings can be dound at console.firebase.google.com
  		- oauth 2.0 client id and secrets should be placed here too.
 	- cd terraform
  	- terraform init



In your code editor, open a terminal. 
- cd terraform
- terraform init --migrate state (use this to avoid any leftovers from the repo)
- terraform plan
