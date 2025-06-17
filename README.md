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
----------------------
Automated using Terraform: 
Of course. Here are the steps to set up the infrastructure for a new project from a freshly cloned repository. This will be perfect for your `README.md`.

***

### Project Deployment Guide

This guide outlines the steps to deploy the ChannelFlow infrastructure to a new Google Cloud project.

#### Prerequisites

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/charsoft/channelFlow.git
    cd channelFlow
    ```
2.  **Install Terraform:** Ensure you have Terraform installed on your local machine.
3.  **Authenticate with Google Cloud:**
    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```
4.  **Configure Project:** Set your active Google Cloud project.
    ```bash
    gcloud config set project your-new-project-id
    ```

#### Step 1: Create and Configure Terraform Backend

Terraform needs a remote backend to store its state. We use a Google Cloud Storage bucket for this.

1.  **Create the GCS Bucket:**
    ```bash
    gsutil mb -p your-new-project-id gs://your-new-project-id-tf-storage
    ```
2.  **Enable Object Versioning:**
    ```bash
    gsutil versioning set on gs://your-new-project-id-tf-storage
    ```
3.  **Update Backend Configuration:** In `terraform/main.tf`, update the `backend "gcs"` block with your new bucket name.
    ```terraform
    # terraform/main.tf

    backend "gcs" {
      bucket = "your-new-project-id-tf-storage" # <-- Change this line
      prefix = "terraform/state"
    }
    ```
4.  **Update Remote State Configuration:** In `terraform/environments/main/main.tf`, update the `terraform_remote_state` data source with the same bucket name.
    ```terraform
    # terraform/environments/main/main.tf

    data "terraform_remote_state" "root" {
      backend = "gcs"
      config = {
        bucket = "your-new-project-id-tf-storage" # <-- Change this line
        prefix = "terraform/state"
      }
    }
    ```

#### Step 2: Populate `terraform.tfvars`

Create a `terraform.tfvars` file in the root `terraform` directory with the following content, replacing the placeholder values:

```
# terraform/terraform.tfvars

project_id             = "your-new-project-id"
target_channel_id      = "your-youtube-channel-id"
gemini_model_name      = "gemini-1.5-pro-latest"
imagen_model_name      = "imagen-3.0-generate-002"
google_client_id       = "your-oauth-2.0-client-id"
google_client_secret   = "your-oauth-2.0-client-secret"
secret_key             = "run-generate_key.py-and-paste-result-here"
```

#### Step 3: Provision Core Infrastructure

This step creates the foundational resources like service accounts, secrets, and API keys.

1.  **Initialize Terraform:**
    ```bash
    terraform -chdir=terraform init
    ```
2.  **Apply the Configuration:**
    ```bash
    terraform -chdir=terraform apply -auto-approve
    ```

#### Step 4: Deploy the CI/CD Pipeline

This step configures the Cloud Build triggers and Cloud Deploy pipeline that will automatically build and deploy your application.

1.  **Initialize the Environment:**
    ```bash
    terraform -chdir=terraform/environments/main init
    ```
2.  **Connect GitHub Repository:** The next command will fail with an error containing a URL.
    *   Open the URL in a browser.
    *   Authorize Google Cloud to connect to your GitHub repository.
    *   **Important:** You may need to do this for both the `global` and your specific project `region` (e.g., `us-central1`). Follow the URLs provided in the error messages.
3.  **Apply the Pipeline Configuration:**
    ```bash
    terraform -chdir=terraform/environments/main apply -auto-approve
    ```
    *Run this command again if it fails the first time after you've connected the repository.*

#### Step 5: Trigger Your First Deployment

Your infrastructure is now fully configured. To deploy your application for the first time, simply push a change to your `main` branch.

```bash
git commit -m "Initial deployment" --allow-empty
git push origin main
```

You can monitor the build and deployment progress in the Google Cloud Console under "Cloud Build" and "Cloud Deploy".



------------------

 -----
Create an artifact repo: 
gcloud artifacts repositories create channelflow-api-repo --project=<<YOUR-PROJECT-ID-HERE>> --repository-format=docker --location=us-central1 --description="ChannelFlow API Docker repository"n
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
