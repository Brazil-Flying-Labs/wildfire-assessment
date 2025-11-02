# assessment_runner.py
from post_fire_assessment.gee_authenticator import GEEAuthenticator


class AssessmentRunner:
    def __init__(self, gee_client: GEEAuthenticator):
        """
        Receives an already initialized GEEAuthenticator instance.
        """
        self.gee = gee_client.ee

    def run_analysis(self):
        """
        Example analysis: directly accesses the Sentinel-2 collection.
        """
        collection = self.gee.ImageCollection("COPERNICUS/S2") \
                             .filterDate("2025-01-01", "2025-01-31")
        print(f"Number of images: {collection.size().getInfo()}")

# Example of execution from a client
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    try:
        gee_client = GEEAuthenticator()
        runner = AssessmentRunner(gee_client)
        runner.run_analysis()

    except Exception as e:
        logging.exception("Unexpected error during processing")
