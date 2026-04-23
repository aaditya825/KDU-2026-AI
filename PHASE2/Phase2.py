import boto3

PDF_MODEL_ID = "meta.llama3-8b-instruct-v1:0"
IMAGE_MODEL_ID = "mistral.ministral-3-8b-instruct"
    
client = boto3.client("bedrock-runtime")

def read_file_as_bytes(path:str) ->bytes :
    with open(path, "rb") as f:
        return f.read()


def build_pdf_request(pdf_path : str) -> dict :
    pdf_bytes = read_file_as_bytes(pdf_path)

    return {
        "modelId":PDF_MODEL_ID,
        "messages":[
            {
                "role":"user", 
                "content":[
                    {
                        "text" : "Read the PDF and summarize it briefly."
                    },
                    {
                        "document" : {
                            "format" : "pdf", 
                            "name" : "sample_pdf", 
                            "source" : {
                                "bytes" : pdf_bytes
                            }
                        }
                    },
                ]
            }
        ],
        "inferenceConfig": {
            "maxTokens": 500,
            "temperature": 0.3
        }
    }


def build_image_request(image_path : str) -> dict :
    image_bytes = read_file_as_bytes(image_path)

    return {
        "modelId":IMAGE_MODEL_ID,
        "messages":[
            {
                "role":"user",
                "content":[
                    {
                        "text" : "Read the image and summarize it briefly."
                    },
                    {
                        "image" : {
                            "format" : "png",
                            "source" : {
                                "bytes" : image_bytes
                            }
                        }
                    },
                ]
            }
        ],
        "inferenceConfig" : {
            "maxTokens" : 500,
            "temperature": 0.3
        }
    }

def invoke(pdf_path : str, image_path: str) :
    pdf_payload= build_pdf_request(pdf_path)
    image_payload= build_image_request(image_path)

    pdf_response = client.converse(
        modelId=pdf_payload["modelId"],
        messages=pdf_payload["messages"],
        inferenceConfig=pdf_payload["inferenceConfig"]
    )

    image_response = client.converse(
        modelId=image_payload["modelId"],
        messages=image_payload["messages"],
        inferenceConfig=image_payload["inferenceConfig"]
    )

    print("=== PDF Summary ===")
    for item in pdf_response["output"]["message"]["content"]:
        if "text" in item:
            print(item["text"])

    print("\n=== Image Summary ===")
    for item in image_response["output"]["message"]["content"]:
        if "text" in item:
            print(item["text"])

    print("\n=== PDF Usage Metadata ===")
    print(pdf_response.get("usage", {}))

    print("\n=== Image Usage Metadata ===")
    print(image_response.get("usage", {}))



if __name__ == "__main__":
    pdf_path = "sample.pdf"
    image_path = "sample.png"
    invoke(pdf_path, image_path)
