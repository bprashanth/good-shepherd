import boto3


class TextractService:
    def __init__(self, region: str = "ap-south-1"):
        self.client = boto3.client("textract", region_name=region)

    def analyze_sync(self, image_bytes: bytes) -> dict:
        """Synchronous Textract call for images < 10MB."""
        response = self.client.analyze_document(
            Document={"Bytes": image_bytes},
            FeatureTypes=["TABLES", "FORMS", "LAYOUT"],
        )
        return response
