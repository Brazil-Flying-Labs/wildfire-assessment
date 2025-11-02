# gee_authenticator.py
import json
import os
from tempfile import NamedTemporaryFile

import ee
from dotenv import load_dotenv


class GEEAuthenticator:
    def __init__(self):
        """
        Initializes the connection to Google Earth Engine using the credentials
        stored in the GEE_PRIVATE_KEY_JSON environment variable from the .env file.
        """
        # Load the local .env file
        load_dotenv()

        # Read the environment variable from .env
        key_json = os.getenv("GEE_PRIVATE_KEY_JSON")
        if key_json is None:
            raise ValueError("GEE_PRIVATE_KEY_JSON environment variable is not set in .env")

        # Convert the JSON string into a dictionary
        key_dict = json.loads(key_json)

        # Initialize GEE using a temporary file
        with NamedTemporaryFile(mode="w+", suffix=".json") as f:
            json.dump(key_dict, f)
            f.flush()
            credentials = ee.ServiceAccountCredentials(key_dict["client_email"], f.name)
            ee.Initialize(credentials)

        # Store the ee object as a class member
        self.ee = ee
