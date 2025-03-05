import boto3
import json

def get_bedrock_client():
    return boto3.client('bedrock-runtime', region_name='us-east-1')

def assess_productivity(activity_data, bedrock):
    try:
        # Define system message
        system_list = [{
            "text": "You are an AI assistant that provides concise productivity scores based on activity data."
        }]

        # Define user message
        message_list = [{
            "role": "user", 
            "content": [{
                "text": f"""Based on this activity data: {json.dumps(activity_data)}
                
                Provide only a productivity score and the factors considered in this format:
                {{
                    "productivity_score": score_0_to_100,
                    "factors_considered": [
                        "factor1_with_brief_explanation",
                        "factor2_with_brief_explanation",
                        "factor3_with_brief_explanation"
                    ]
                }}"""
            }]
        }]

        # Configure inference parameters
        inference_config = {
            "maxTokens": 500,
            "temperature": 0.5,
            "topP": 0.8
        }

        # Prepare request body
        request_body = {
            "schemaVersion": "messages-v1",
            "messages": message_list,
            "system": system_list,
            "inferenceConfig": inference_config
        }

        # Invoke the model
        response = bedrock.invoke_model_with_response_stream(
            modelId="us.amazon.nova-lite-v1:0",
            body=json.dumps(request_body)
        )

        # Process the response stream
        full_response = ""
        stream = response.get("body")
        if stream:
            for event in stream:
                chunk = event.get("chunk")
                if chunk:
                    chunk_json = json.loads(chunk.get("bytes").decode())
                    content_block_delta = chunk_json.get("contentBlockDelta")
                    if content_block_delta:
                        full_response += content_block_delta.get("delta", {}).get("text", "")

        # Parse the response as JSON
        try:
            return json.loads(full_response)
        except json.JSONDecodeError:
            return {
                "productivity_score": 0,
                "factors_considered": ["Error processing response"],
                "error": full_response
            }

    except Exception as e:
        print(f"Error in assess_productivity: {str(e)}")
        return {
            "productivity_score": 0,
            "factors_considered": ["Error in assessment"],
            "error": str(e)
        }

def lambda_handler(event, context):
    try:
        print("Starting productivity assessment")
        activity_data = event.get('activity_pattern', {})
        bedrock = get_bedrock_client()
        return assess_productivity(activity_data, bedrock)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "productivity_score": 0,
            "factors_considered": ["Error in lambda execution"],
            "error": str(e)
        }
