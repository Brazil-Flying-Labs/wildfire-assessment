import ee
import json
from config.settings import CREDENTIALS_PATH


def initialize_gee():
    """Inicializa o Google Earth Engine com credenciais de conta de serviço."""
    try:
        service_account_dict = {
            "Colar o conteudo de autenticação do json"
        }
        credentials = ee.ServiceAccountCredentials(email='', key_data=json.dumps(service_account_dict))
        ee.Initialize(credentials, project='well-stem')
        print("Google Earth Engine inicializado com sucesso.")
    except ee.EEException as e:
        print(f"Erro ao inicializar o Google Earth Engine: {e}")
        raise
    except Exception as e:
        print(f"Erro inesperado durante a inicialização: {e}")
        raise