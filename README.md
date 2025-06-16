# channelFlow
Hackathon entry!

Running it locally:

(details for running it locally are coming soon...)




Running it in GCP
How to set up:
- Create a Google Cloud project
- Manually create the OAuth Client ID and Secret in GCP Console
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
 	- .\.venv\Scripts\Activate.ps1
- Now install the requirements into the virtual environment	
	- pip install -r requirements.txt
