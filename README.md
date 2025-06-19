# channelFlow
Hackathon entry!

Running it Locally:
You still have to set up the OAuth 2.0 client in your GCP project, since this app requires users to authentication with Google Cloud.



Setting it up in GCP

Create a Google Cloud project

***
#### install google cloud sdk
1. **authenticate to google cloud:**  
2. **Set your project to the one you just created**
3. **Set up the environment for Python**
	```bash
 		pyenv install 3.12.4
  	```
 4. **Create the virtual environment**
	```bash
	 	python -m venv .venv
 	```
 
5. **Activate the virtual environment**
   	```bash
	 	.\\.venv\\Scripts\\Activate.ps1
    	```
    
6. **Now install the requirements into the virtual environment**	
	```bash
 		pip install -r requirements.txt
 	```
	
- Enable VertexAI service (go to the api keys page and set this to "web")
- Enable YouTube API (configure the app to allow us to read their youtube account)
- Enable the Firestore API and create a default database. Make it in the nam5 region, and use standard security.
------ 
FOR THE TRANSCRIBING AGENT
------
1. Create a service account
Go to: https://console.cloud.google.com/iam-admin/serviceaccounts

Click Create Service Account

Name: channel-flow-transcriber

Role: Storage Object Viewer + Storage Legacy Signer (optional but helps)

Click Create and Continue

On the final screen, click “Done”

2. Download the key
Click on your new service account

Go to "Keys" tab

Click "Add Key" → "Create new key"

Choose JSON

Save the file as service-account-key.json in your project folder

--------
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
         - In "Audience", click "make external" but keep the state of TESTING selected. I needed this because my YouTube account is under another domain.
  - Copy the Google_Client_Id, paste it in the .env.local and the .env files on the project root
  - Copy the Goole_Client_Secret, paste it in the environment variables as well
  - Paste both values in the terraform.tfvars relative environment fields
- Create a storage bucket (to be used as terraform backend)
	- copy the name, paste it into the terraform/main.tf somewhere around 17
----------------------
Automated using Terraform: 


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

TROUBLE WITH IAM?

----------------------
```markdown
# IAM Permissions Utility Scripts

This directory contains utility scripts to help diagnose and resolve common IAM permission issues when setting up and deploying the ChannelFlow application on Google Cloud.

Prequisites

Before using these scripts, you must have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated. The scripts are designed to be run in a bash environment, such as the Google Cloud Shell.

To use these scripts in Cloud Shell:
1. Upload the necessary scripts to your Cloud Shell environment.
2. Make them executable. For example: `chmod +x create_custom_role.sh`

---

### 1. `create_custom_role.sh`

This script creates a custom IAM role required by the application's service account to access specific Storage APIs. This is a necessary first step.

**Usage:**
```bash
./create_custom_role.sh [PROJECT_ID]
```

**Example:**
```bash
./create_custom_role.sh my-gcp-project
```

---

### 2. `grant_cloud_run_sa_roles.sh`

The application runs in Cloud Run using a specific service account. This script grants all the necessary permissions for that service account to function correctly, including access to Datastore, Secret Manager, and the custom Storage role.

**Usage:**
```bash
./grant_cloud_run_sa_roles.sh [PROJECT_ID] [SERVICE_ACCOUNT_EMAIL]
```

**Example:**
```bash
# Replace with the email of the service account used by your Cloud Run service
./grant_cloud_run_sa_roles.sh my-gcp-project channel-flow-svc-sa@my-gcp-project.iam.gserviceaccount.com
```

---

### 3. `grant_cloud_deployer_roles.sh`

The CI/CD pipeline uses a dedicated service account to deploy the application. This script grants that account the permissions it needs to manage deployments, access Artifact Registry, and more.

**Usage:**
```bash
./grant_cloud_deployer_roles.sh [PROJECT_ID] [SERVICE_ACCOUNT_EMAIL]
```

**Example:**
```bash
# Replace with the email of the service account used by Cloud Deploy
./grant_cloud_deployer_roles.sh my-gcp-project my-deployer-sa@my-gcp-project.iam.gserviceaccount.com
```

---

### 4. `check_permissions.sh`

If you are still facing permissions issues, this script can be used as a general-purpose tool to inspect the roles assigned to any user or service account on the project.

**Usage:**
```bash
./check_permissions.sh [PROJECT_ID] [MEMBER_EMAIL]
```

**Example:**
```bash
# Check a service account
./check_permissions.sh my-gcp-project my-sa@my-gcp-project.iam.gserviceaccount.com

# Check a user
./check_permissions.sh my-gcp-project user@example.com
```
```
 -----
-----
Create a JWT_SECRET_KEY for the youtube connection
(skip attempts to make Terraform do it...)

1.  **Generate a Secret Key:**
    First, you need a strong, random key. Run this command in your local terminal to generate one:
    ```bash
    python -c "import secrets; print(secrets.token_hex(32))"
    ```
    Copy the long string it prints out.

2.  **Create the Secret in Secret Manager:**
    *   In the Google Cloud Console, navigate to **Security** -> **Secret Manager**.
    *   Click **+ CREATE SECRET**.
    *   For the **Secret name**, enter exactly `jwt-secret-key`. This must match the name the application is looking for.
    *   In the **Secret value** field, paste the key you just generated.
    *   Leave all other options as default and click **Create secret**.

That's it. Your application is already configured to look for a secret with that exact name, and the `grant_cloud_run_sa_roles.sh` script we created earlier has already given your Cloud Run service account the `Secret Manager Secret Accessor` role, so it has permission to read it.

Once you push your latest application code, the backend will be able to fetch this secret and your JWT authentication should work.

We can definitely revisit the Terraform configuration to clean it up and automate this whenever you're ready. Good luck with the push

