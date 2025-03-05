import boto3
import json
from datetime import datetime

def get_bedrock_client():
    return boto3.client('bedrock-runtime', region_name='us-east-1')

def analyze_productivity(visual_data, bedrock):
    try:
        # Extract content from nested structure with improved error handling
        content_text = ""
        if isinstance(visual_data, dict):
            if 'visual_analysis' in visual_data:
                visual_analysis = visual_data.get('visual_analysis', {})
                output = visual_analysis.get('output', {})
                message = output.get('message', {})
                content = message.get('content', [])
                if content and isinstance(content, list):
                    content_text = content[0].get('text', '')
            elif 'output' in visual_data:
                message = visual_data.get('output', {}).get('message', {})
                content = message.get('content', [])
                if content and isinstance(content, list):
                    content_text = content[0].get('text', '')

        # Enhanced prompt for better productivity analysis
        message_list = [{
            "role": "user", 
            "content": [{
                "text": f"""Analyze this screen activity data and provide a concise summary:

                Screen Data: {content_text}

                Focus on:
                1. Active vs. Inactive UI Elements:
                   - Which tabs and features are currently active
                   - Pattern of active vs. inactive elements
                
                2. Application Usage:
                   - Main applications visible
                   - How they are being used together
                
                3. Workspace Organization:
                   - Overall layout and structure
                   - File organization and accessibility
                
                4. Productivity Indicators:
                   - Signs of active project work
                   - Evidence of organized workflow
                
                Provide a single, focused paragraph that evaluates productivity based on these UI elements.
                """
            }]
        }]

        # Enhanced system prompt for more precise analysis
        system_prompt = {
            "text": """You are an expert UI activity analyzer specializing in productivity assessment.
                      Focus on identifying patterns in UI element usage that indicate productive work habits.
                      Analyze how the arrangement and state of UI elements reflect user engagement and workflow efficiency."""
        }

        # Configure inference parameters for more consistent output
        request_body = {
            "schemaVersion": "messages-v1",
            "messages": message_list,
            "system": [system_prompt],
            "inferenceConfig": {
                "maxTokens": 300,
                "temperature": 0.4,  # Lower temperature for more consistent analysis
                "topP": 0.9,
                "stopSequences": []
            }
        }

        # Get response from Bedrock with error handling
        try:
            response = bedrock.invoke_model_with_response_stream(
                modelId="us.amazon.nova-lite-v1:0",
                body=json.dumps(request_body)
            )
        except Exception as e:
            raise Exception(f"Bedrock API error: {str(e)}")

        # Process stream with improved error handling
        full_response = ""
        stream = response.get("body")
        if stream:
            try:
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        chunk_json = json.loads(chunk.get("bytes").decode())
                        content_block_delta = chunk_json.get("contentBlockDelta")
                        if content_block_delta:
                            full_response += content_block_delta.get("delta", {}).get("text", "")
            except Exception as e:
                raise Exception(f"Stream processing error: {str(e)}")

        current_time = datetime.now().isoformat()

        # Enhanced response structure
        return {
            "productivity_analysis": {
                "summary": full_response,
                "timestamp": current_time,
                "status": "completed",
                "analysis_type": "ui_activity",
                "data_quality": "success" if content_text else "no_input_data"
            }
        }
    except Exception as e:
        current_time = datetime.now().isoformat()
        print(f"Error in analyze_productivity: {str(e)}")
        return {
            "productivity_analysis": {
                "error": str(e),
                "timestamp": current_time,
                "status": "failed",
                "analysis_type": "ui_activity",
                "data_quality": "error"
            }
        }

def lambda_handler(event, context):
    try:
        print("Starting productivity analysis")
        print(f"Event: {json.dumps(event)}")
        
        bedrock = get_bedrock_client()
        analysis_result = analyze_productivity(event, bedrock)
        
        return analysis_result
        
    except Exception as e:
        current_time = datetime.now().isoformat()
        return {
            "error": str(e),
            "timestamp": current_time,
            "status": "failed",
            "analysis_type": "ui_activity"
        }
