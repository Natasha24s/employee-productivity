import boto3
import json
import base64

def get_bedrock_client():
    return boto3.client('bedrock-runtime', region_name='us-east-1')

def analyze_image_with_nova(image_data, bedrock):
    try:
        # Define system message
        system_list = [{
            "text": "You are an expert at analyzing screenshots and UI elements."
        }]

        # Define message with image and prompt
        message_list = [{
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": "png",  # Changed from "base64" to "png"
                        "source": {"bytes": image_data}
                    }
                },
                {
                    "text": """Analyze this screenshot and provide:
                        1. All visible applications and windows
                        2. UI elements and their states
                        3. Any visible timestamps
                        4. User interactions visible
                        5. Type of work being performed"""
                }
            ]
        }]

        # Define inference parameters
        inf_params = {
            "maxTokens": 300,
            "topP": 0.1,
            "topK": 20,
            "temperature": 0.3
        }

        # Construct the request body
        request_body = {
            "schemaVersion": "messages-v1",
            "messages": message_list,
            "system": system_list,
            "inferenceConfig": inf_params
        }

        response = bedrock.invoke_model(
            modelId="us.amazon.nova-lite-v1:0",
            body=json.dumps(request_body)
        )
        
        return json.loads(response.get('body').read())
    except Exception as e:
        print(f"Error in analyze_image_with_nova: {str(e)}")
        raise

def lambda_handler(event, context):
    try:
        print("Starting visual analysis process")
        print(f"Event: {json.dumps(event)}")
        
        # Extract image data from input
        input_data = json.loads(event.get('input', '{}'))
        image_data = input_data.get('image_data')
        
        if not image_data:
            raise ValueError("No image data provided")
        
        # Initialize Bedrock client
        bedrock = get_bedrock_client()
        
        # Analyze image
        analysis_result = analyze_image_with_nova(image_data, bedrock)
        
        return analysis_result
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
