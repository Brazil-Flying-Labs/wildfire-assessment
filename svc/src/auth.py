import json

import ee
from config.settings import CREDENTIALS_PATH


def initialize_gee():
    """Inicializa o Google Earth Engine com credenciais de conta de serviço."""
    try:
        service_account_dict = {
            "type": "service_account",
            "project_id": "well-stem",
            "private_key_id": "549be8c54c1c9a6efd0d2b2248c845ac39191706",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC2wUwMQnYY97kH\nxNoHObzHKMcFYmJEbyL8Rbehi6oAqn4OZ0d/pVv8QiAw1hLYE7C4vgRpovOZrHnx\nRzPLNCZ4SSYOo6zK1T6zfEIBo7+HQ4Uu86CeNMh1uir+/f8cYH9mPbVcEsWt6InY\n/xEr6V4wLbHK2mZY5hyww9MX6hOOg95ulJ1XpBBuB0HamIf4Wnhd3LYjAqGjjVQz\n7dceZEF6JfqTGfHglTWo0Zpok14WsfI1mxDMaYuTQjSjZONcxPN23cGQMnxba3fQ\n34MKtt/vweS2uMaCN+GXZBY32LQdnJFuEWKUxEkqKcIgdsL2t086WRYKoXrYPyh3\nHKpSMztzAgMBAAECggEAQ4yTzs4794OMxRXaHqSVJanpUhCo0LGhZUxhkNjeF8vs\ntucusrwMkWNhoZtmsK4qekZlvCPqVUk+c1OFjdyzQW+MHQobYodKWy4Y+aEsOFNZ\nJV8QZZmN5JHQtZptUnBKdqBlaehYX6zdUrMIhkoGMdmZ5ygtfztirGVdH3A6FUkB\nGU1ieREAP5urckdPf1hTn+cILaPiqHIBrsVdHBs8kJqbEZzzEX9jMpgMHvJKklWx\nkQX+io9uJ9sUILmaEQOZjaJT83MQX9A2OKwASFxbiyHL7XvJ9KaZkf57sNfoq9ew\nTbz86U7VRqxMxFGoMRyYY/DEZAXuPhUg6tfNlqVeMQKBgQDrDkf9XXJsbRcwKeDM\n9UpfB/BBUmBp2pjoz3WqkUJsuzFBwq+vK1/6x6S6iRY8ZaA1OiyYBMFrDpyHk8B9\n2CN2Qix3l0Ejdc1BM4N+qHGDeyCobta8wnm4EYe/kC7tQFmM3hL6xXN+fE5GOR2c\n3zOv+2Be/861VPs+nwLKVzwV0QKBgQDHCgPYAAh8C0DUwnWF1g9SkMmC9Bbncmo3\nltkIhkJWUHlBq69X4x3rbtcQNlWVxEeRkh5He9XLoYW+hZz1bhTqMD1BA04FqEzV\nCLLk1s+S4HxcukbVWi0S2l6AGaQFsfcT/4iFN9f0FeE9MhvdB9wKkkuVGsR1lb7H\nqVQ2XvvaAwKBgQDA36cSr2sErT8ptjNP+rZb5Bewgfe65DQ0VIcovqjSr4drfmTK\nR70p+kehCHvGc11ST7nnw38yaXrnhMWefYwbrZDvUJ2Si0cxCSQM+gqq6I2Tp99s\nY+ecskXBWn4nD3ZrsI3CV+K9FyLjXFqALmYrMQmS6jSjdmfyqmePwKT9AQKBgErZ\n41QpvwcXHExmzNeGBsEgHggXTz2+817wZbIk+3GGVfNyY0CD8s6FIm/AXzMxW1DN\nSIHNejtYBPn/OWW6/jaL6Z03ZvINtscuvEf+2JT9wwcELnsxrF24rW0zN1HE+YwV\nvvuKYrYyPEBNRdk7iW6YUcBDDrrBk7t2XGsOEVyNAoGBAM4SdhhzWoxaxCVUhk1J\n+DcY9Sf+Wv10UzqZ2kpxEaXsa+jBpC+I2FCtwKdxZtjU735g4THpyBnxkulENpNJ\n7WC3RxNbr1OPtcBsOAnpK8F9kAVPkAwjNviBPAvdEzZzHWHnSetSF8FuPbG9XRWE\n9VmqnMXEOCQmj2CoWXw4KqQG\n-----END PRIVATE KEY-----\n",
            "client_email": "gee-service-account@well-stem.iam.gserviceaccount.com",
            "client_id": "109527695298862765701",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/gee-service-account%40well-stem.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com",
        }
        credentials = ee.ServiceAccountCredentials(
            email="", key_data=json.dumps(service_account_dict)
        )
        ee.Initialize(credentials, project="well-stem")
        print("Google Earth Engine inicializado com sucesso.")
    except ee.EEException as e:
        print(f"Erro ao inicializar o Google Earth Engine: {e}")
        raise
    except Exception as e:
        print(f"Erro inesperado durante a inicialização: {e}")
        raise
