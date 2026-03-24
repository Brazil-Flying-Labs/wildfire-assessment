"""Fetch Grafana Cloud credentials from Secrets Manager and print OTEL env var exports.

Usage in docker-compose command:
    eval $(python configure_otel.py 2>/dev/null) && opentelemetry-instrument ...

When SKIP_AWS_SECRETS=1 (tests/CI), this prints nothing and OTEL runs without auth.
"""

import base64
import json
import os
import sys


def main():
    if os.environ.get("SKIP_AWS_SECRETS") == "1":
        return

    try:
        import boto3

        session = boto3.Session()
        client = session.client("secretsmanager")
        env = os.environ.get("ENV", "local")
        secret = json.loads(client.get_secret_value(SecretId=env)["SecretString"])

        endpoint = secret.get("GRAFANA_CLOUD_OTLP_ENDPOINT", "")
        instance_id = secret.get("GRAFANA_CLOUD_INSTANCE_ID", "")
        api_key = secret.get("GRAFANA_CLOUD_API_KEY", "")

        if instance_id and api_key and endpoint:
            credentials = f"{instance_id}:{api_key}"
            encoded = base64.b64encode(credentials.encode()).decode()
            print(f'export OTEL_EXPORTER_OTLP_ENDPOINT="{endpoint}"')
            print(f'export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic {encoded}"')
    except Exception as e:
        print(f"# Warning: Could not configure OTEL: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
