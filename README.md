# wildfire-assessment

AI-based assessment and classification of fire damage caused by wildfire in Luiz Antônio Experimental Station - Jataí

# Initial Setup

Run `python3 -m venv venv` to create a virtual environment.
Run `source venv/bin/activate` to activate the virtual environment.
Run `pip install -r requirements.txt` to install the required packages.

# Dependencies

In order to run the application, you need to have a AWS profile configured with the necessary permissions to access the S3 bucket. The profile must be named as bfl.

Rode o seguinte comando e forneça as credenciais da AWS:

```bash
aws configure --profile bfl
```

# Environment Variables

You need to create a `.env` file in the root directory of the project with the following variables:

```base
cp .env.example .env
```

Open the `.env` file and set the variables with the correct values.

In addition to the AWS credentials already used by the project, the backend now needs to know which Auth0 API audience it should trust when validating incoming Bearer tokens. Set the following key using the same identifier configured in Auth0 (the value must match `REACT_APP_AUTH0_AUDIENCE` from the UI):

```
AUTH0_API_AUDIENCE=https://wildfire-assessment-api
```

When the configured Auth0 API does not embed the user's email in the access token payload, the backend can fall back to the Auth0 Management API to retrieve it. Provide a machine-to-machine application's credentials so the Django API can request a Management token on demand:

```
AUTH0_MANAGEMENT_CLIENT_ID=<your-m2m-client-id>
AUTH0_MANAGEMENT_CLIENT_SECRET=<your-m2m-client-secret>
# Optional when using the default value
AUTH0_MANAGEMENT_AUDIENCE=https://<your-auth0-domain>/api/v2/
```

If you expose the email through a custom JWT claim instead, set `AUTH0_EMAIL_CLAIM` with the claim name so the backend does not need to call the Management API.

## Gmail SMTP setup

Google no longer allows username/password logins from "less secure apps". To let the backend send emails through Gmail you must use an [app password](https://support.google.com/accounts/answer/185833). Use a dedicated account (or service account) and follow these steps:

- Enable 2-Step Verification on the Gmail account.
- Visit Google Account → Security → App passwords and create a new password for the "Mail" app.
- Copy the 16-character app password and store it in your `.env` file or secret manager;
- Restart the backend so it loads the new credentials.

Trying to authenticate with the normal account password will lead to `SMTPAuthenticationError (535)` even if the password is correct.

# Usage

Run `make reset` the first time to setup your environment, Subsequent use can be `make up`. (If you add any new requirement to requirements.txt, a `make reset` will be required).

If your OS doesn't support `make` commands, you can simply do `docker-compose down -v --rmi all --remove-orphans` followed by `docker-compose up --build -d` for the first time, the subsequent times you can just do `docker-compose up`.

You need to create a first time superuser. Shell into the api container and run:

```shell
python manage.py createsuperuser
```

After make command ends, you can access the Admin interface using:

https://localhost:8081/admin/

Swagger UI lives in:

https://localhost:8081/api/schema/swagger-ui

## API authentication

Every REST endpoint exposed by the Django API now requires a valid Auth0 access token. Include the token issued for the `AUTH0_API_AUDIENCE` in the `Authorization` header of each request:

```
curl -H "Authorization: Bearer <access_token>" https://localhost:8081/ecological_reserve/
```

Tokens issued for a different audience (for example the Auth0 Management API) will be rejected with `401 Unauthorized`.

On the first request made with a new Auth0 identity the backend automatically creates a matching Django user and marks it as inactive. An administrator must activate the user (through `/admin/`) before subsequent API calls succeed.

# IAC

Run `terraform init -backend-config="backends/dev.hcl"` to initialize the Terraform backend.
Run `terraform plan -var-file="vars/dev.tfvars"` to see the changes that will be applied.
Run `terraform apply -var-file="vars/dev.tfvars"` to apply the changes. This is mostly unnecessary since we want to apply using the GitHub Actions workflow.

```

```
