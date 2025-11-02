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
cp .env.template .env
```

Open the `.env` file and set the variables with the correct values.

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

https://127.0.0.1:8081/api/schema/swagger-ui

# IAC

Run `terraform init -backend-config="backends/dev.hcl"` to initialize the Terraform backend.
Run `terraform plan -var-file="vars/dev.tfvars"` to see the changes that will be applied.
Run `terraform apply -var-file="vars/dev.tfvars"` to apply the changes. This is mostly unnecessary since we want to apply using the GitHub Actions workflow.

```

```
