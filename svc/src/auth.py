import ee
from config.settings import CREDENTIALS_PATH


def initialize_gee():
    """Inicializa o Google Earth Engine com credenciais de conta de serviço."""
    try:
        credentials = ee.ServiceAccountCredentials('', CREDENTIALS_PATH)
        ee.Initialize(credentials, project='well-stem')
        print("Google Earth Engine inicializado com sucesso.")
    except ee.EEException as e:
        print(f"Erro ao inicializar o Google Earth Engine: {e}")
        raise
    except Exception as e:
        print(f"Erro inesperado durante a inicialização: {e}")
        raise