import os


class AppConfig:
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

    CASUAL_MODEL_ID = os.getenv(
        "CASUAL_MODEL_ID",
        "meta.llama3-8b-instruct-v1:0"
    )

    COMPLEX_MODEL_ID = os.getenv(
        "COMPLEX_MODEL_ID",
        "meta.llama3-8b-instruct-v1:0"
    )

    ROUTER_MODEL_ID = os.getenv(
        "ROUTER_MODEL_ID",
        "meta.llama3-8b-instruct-v1:0"
    )

    EMBED_MODEL_NAME = os.getenv(
        "EMBED_MODEL_NAME",
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    SEMANTIC_CONFIDENCE_THRESHOLD = float(
        os.getenv("SEMANTIC_CONFIDENCE_THRESHOLD", "0.18")
    )
