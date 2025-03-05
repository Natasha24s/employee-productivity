import streamlit as st
import requests
import json
from datetime import datetime
import base64
from io import BytesIO
import pandas as pd
from PIL import Image
import boto3
import time

# Configure page settings
st.set_page_config(
    page_title="Employee Productivity Tracking",
    page_icon="📊",
    layout="wide"
)

# API Configuration
API_ENDPOINT = 'https://wt7zuh1n3f.execute-api.us-east-1.amazonaws.com/prod/track'

def get_image_format(file_bytes):
    """Get the format of the image file"""
    try:
        img = Image.open(file_bytes)
        return img.format
    except Exception:
        return None

def auto_crop(img):
    """Auto-crop image to remove empty spaces"""
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def aggressive_compress(img):
    """Aggressively compress image if needed"""
    for size in [(400, 400), (300, 300), (200, 200)]:
        buffer = BytesIO()
        img_copy = img.copy()
        img_copy.thumbnail(size)
        img_copy.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        if len(buffer.getvalue()) <= 250000:
            return buffer
    return None

def verify_png_format(buffer):
    """Verify that the buffer contains PNG data"""
    try:
        img = Image.open(buffer)
        return img.format == 'PNG'
    except Exception:
        return False

def compress_image(uploaded_file):
    """Compress the image and ensure PNG format with size limits"""
    try:
        img = Image.open(uploaded_file)
        
        # First check if original file is already small enough
        original_size = len(uploaded_file.getvalue())
        if original_size <= 250000 and img.format == 'PNG':  # Only skip compression for small PNGs
            uploaded_file.seek(0)
            return BytesIO(uploaded_file.getvalue())
        
        # Convert to RGB if needed
        if img.mode not in ('RGBA', 'RGB'):
            img = img.convert('RGB')
        
        # Auto crop and resize if needed
        img = auto_crop(img)
        MAX_SIZE = (500, 500)
        img.thumbnail(MAX_SIZE, Image.LANCZOS)
        
        # Always save as PNG
        buffer = BytesIO()
        img.save(buffer, format='PNG', optimize=True, quality=85)
        buffer.seek(0)
        
        final_size = len(buffer.getvalue())
        if final_size > 250000:
            st.warning("Image is large, attempting further compression...")
            compressed_buffer = aggressive_compress(img)
            if compressed_buffer:
                return compressed_buffer
            
            # Final attempt with grayscale
            img = img.convert('L')
            buffer = BytesIO()
            img.save(buffer, format='PNG', optimize=True, quality=70)
            buffer.seek(0)
            
        return buffer
    except Exception as e:
        st.error(f"Error compressing image: {str(e)}")
        return None

def get_image_base64(file):
    """Convert uploaded file to base64"""
    try:
        bytes_data = file.getvalue()
        base64_string = base64.b64encode(bytes_data).decode()
        return base64_string
    except Exception as e:
        st.error(f"Error converting image to base64: {str(e)}")
        return None

def validate_input(image_base64):
    """Validate the input before sending to API"""
    if not image_base64:
        return False, "No image data provided"
    
    size_in_bytes = len(image_base64.encode('utf-8'))
    if size_in_bytes > 262000:
        return False, f"Image too large ({size_in_bytes} bytes). Maximum allowed is 262144 bytes."
    
    return True, ""
def poll_execution_status(execution_arn, max_attempts=30, delay=2):
    """Poll Step Functions execution status"""
    sfn_client = boto3.client('stepfunctions', region_name='us-east-1')
    
    for _ in range(max_attempts):
        try:
            response = sfn_client.describe_execution(
                executionArn=execution_arn
            )
            
            status = response['status']
            
            if status == 'SUCCEEDED':
                output = response.get('output', '{}')
                try:
                    parsed_output = json.loads(output)
                    return {
                        'status': status,
                        'output': parsed_output
                    }
                except json.JSONDecodeError as e:
                    st.error(f"Error parsing Step Functions output: {e}")
                    return {
                        'status': 'ERROR',
                        'error': f"Invalid JSON output"
                    }
                    
            elif status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
                error_info = response.get('error', 'Unknown error')
                st.error(f"Step Functions execution failed: {error_info}")
                return {
                    'status': status,
                    'error': error_info
                }
                
            time.sleep(delay)
            
        except Exception as e:
            st.error(f"Error polling Step Functions: {e}")
            return {
                'status': 'ERROR',
                'error': str(e)
            }
    
    return {
        'status': 'TIMEOUT',
        'error': 'Maximum polling attempts reached'
    }

def display_visual_analysis(analysis_data):
    """Display Visual Analysis Results"""
    st.subheader("📸 Visual Analysis Results")
    
    try:
        if isinstance(analysis_data, dict):
            if 'output' in analysis_data:
                if 'message' in analysis_data['output']:
                    if 'content' in analysis_data['output']['message']:
                        content = analysis_data['output']['message']['content']
                        if content and isinstance(content, list):
                            analysis_text = content[0].get('text', '')
                            st.markdown(analysis_text)
                            return
    except Exception as e:
        st.error(f"Error processing visual analysis: {str(e)}")
        st.warning("Could not parse visual analysis data structure")

def display_activity_pattern(pattern_data):
    """Display Activity Pattern Analysis"""
    st.subheader("📊 Activity Pattern Analysis")
    
    try:
        if isinstance(pattern_data, dict):
            if 'productivity_analysis' in pattern_data:
                summary = pattern_data['productivity_analysis'].get('summary', '')
                if summary:
                    st.markdown("### Summary")
                    st.markdown(summary)
                
                timestamp = pattern_data['productivity_analysis'].get('timestamp', '')
                if timestamp:
                    st.markdown("### Timestamp")
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        formatted_time = dt.strftime("%B %d, %Y %I:%M %p")
                        st.info(formatted_time)
                    except:
                        st.info(timestamp)
                
                status = pattern_data['productivity_analysis'].get('status', '')
                if status:
                    st.markdown(f"**Status:** {status.capitalize()}")
                    
    except Exception as e:
        st.error(f"Error processing activity pattern: {str(e)}")

def display_productivity_assessment(assessment_data):
    """Display Productivity Assessment Results"""
    st.subheader("📈 Productivity Assessment")
    
    try:
        if isinstance(assessment_data, dict):
            if 'productivity_score' in assessment_data:
                score = assessment_data['productivity_score']
                st.markdown("### Overall Score")
                st.progress(score / 100)
                st.metric("Productivity Score", f"{score}%")
            
            if 'factors_considered' in assessment_data:
                st.markdown("### 🎯 Factors Considered")
                for factor in assessment_data['factors_considered']:
                    st.markdown(f"- {factor}")
            
            if 'error' in assessment_data:
                st.error(f"Assessment Error: {assessment_data['error']}")
                    
    except Exception as e:
        st.error(f"Error processing productivity assessment: {str(e)}")

def trigger_analysis(image_base64):
    """Trigger the analysis workflow through API Gateway"""
    is_valid, error_message = validate_input(image_base64)
    if not is_valid:
        st.error(error_message)
        return None

    try:
        payload = {
            "input": json.dumps({
                "image_data": image_base64
            }, separators=(',', ':'))
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        with st.spinner('Starting analysis...'):
            response = requests.post(
                API_ENDPOINT,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                execution_arn = result.get('executionArn')
                
                if execution_arn:
                    st.info(f"Analysis started...")
                    
                    status = poll_execution_status(execution_arn)
                    
                    if status.get('status') == 'SUCCEEDED':
                        output = status.get('output', {})
                        
                        return {
                            'visual_analysis': output.get('visual_analysis', {}),
                            'activity_pattern': output.get('activity_pattern', {}),
                            'productivity_assessment': output.get('productivity_assessment', {})
                        }
                    else:
                        st.error(f"Analysis failed: {status.get('error')}")
                        return None
                else:
                    st.error("No execution ARN received")
                    return None
            else:
                st.error(f"API Error: {response.status_code}")
                st.error(f"Response: {response.text}")
                return None
                
    except Exception as e:
        st.error(f"Error in analysis: {str(e)}")
        return None

def main():
    st.title('🎯 Employee Productivity Tracking System')
    
    st.warning("Please note: Images will be compressed and converted to PNG format. For best results, use images under 1MB.")
    
    uploaded_file = st.file_uploader(
        "Upload Screenshot",
        type=['png', 'jpg', 'jpeg'],
        help="Upload a screenshot to analyze productivity"
    )
    
    if uploaded_file is not None:
        file_size = len(uploaded_file.getvalue()) / 1024
        original_format = get_image_format(uploaded_file)
        st.info(f"Original file size: {file_size:.2f} KB ({original_format} format)")
        
        compressed_file = compress_image(uploaded_file)
        if compressed_file:
            compressed_size = len(compressed_file.getvalue()) / 1024
            
            if compressed_size >= file_size:
                st.info(f"Converted to PNG: {compressed_size:.2f} KB")
            else:
                st.success(f"Compressed and converted to PNG: {compressed_size:.2f} KB")
            
            st.image(compressed_file, caption='Uploaded Screenshot', use_container_width=True)
            
            if st.button('🔍 Analyze Productivity'):
                image_base64 = get_image_base64(compressed_file)
                
                if image_base64:
                    base64_size = len(image_base64.encode('utf-8'))
                    
                    if base64_size > 262000:
                        st.error(f"Base64 encoded size ({base64_size} bytes) exceeds limit")
                        return
                    
                    with st.spinner('Analyzing...'):
                        result = trigger_analysis(image_base64)
                    
                    if result:
                        with st.container():
                            display_visual_analysis(result.get('visual_analysis'))
                            display_activity_pattern(result.get('activity_pattern'))
                            display_productivity_assessment(result.get('productivity_assessment'))
                            
                            report = {
                                'timestamp': datetime.now().isoformat(),
                                'analysis_results': result
                            }
                            
                            st.download_button(
                                label="📥 Download Analysis Report",
                                data=json.dumps(report, indent=2),
                                file_name="productivity_report.json",
                                mime="application/json"
                            )
                    else:
                        st.error("Failed to process the analysis")
                else:
                    st.error("Failed to process the image")

if __name__ == '__main__':
    main()
