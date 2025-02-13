import requests
import json
import os
from dotenv import load_dotenv
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables at the start
load_dotenv()

def check_login_type(email):
    """Check the login type for the given email address.
    
    Args:
        email (str): The email address to check
        
    Returns:
        dict: The login type response from Ed or None if request fails
    """
    url = "https://us.edstem.org/api/login_type"
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'origin': 'https://edstem.org',
    }
    
    payload = {
        "login": email,
        "force_code": False,
        "force_reauth": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Login type check failed: {e}")
        return None

def get_token(email, password):
    """Get authentication token using email and password.
    
    Args:
        email (str): User's email address
        password (str): User's password
        
    Returns:
        str: Authentication token or None if request fails
    """
    url = "https://us.edstem.org/api/token"
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'origin': 'https://edstem.org',
    }
    
    payload = {
        "login": email,
        "password": password
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Token request failed: {e}")
        return None

def get_all_thread_links(token, course_id="72657"):
    """Get all thread links using Ed's API endpoint directly."""
    print("Collecting all thread links...")
    
    headers = {
        'x-token': token,
        'accept': 'application/json',
    }
    
    all_threads = []
    offset = 0
    limit = 30
    
    while True:
        url = f"https://us.edstem.org/api/courses/{course_id}/threads?limit={limit}&offset={offset}&sort=new"
        print(f"Fetching threads with offset {offset}...")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('threads'):
                break
                
            threads = data['threads']
            all_threads.extend([
                f"https://edstem.org/us/courses/{course_id}/discussion/{thread['id']}"
                for thread in threads
            ])
            
            if len(threads) < limit:
                break
                
            offset += limit
            print(f"Collected {len(all_threads)} threads so far...")
            
        except Exception as e:
            print(f"Error fetching threads: {str(e)}")
            break
    
    print(f"Total threads collected: {len(all_threads)}")
    return all_threads

def get_thread_data(token, thread_id):
    """Fetch detailed data for a specific thread."""
    print(f"Fetching data for thread {thread_id}...")
    
    headers = {
        'x-token': token,
        'accept': 'application/json',
    }
    
    url = f"https://us.edstem.org/api/threads/{thread_id}?view=1"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"Error fetching thread data: {str(e)}")
        return None

def clean_content(content):
    """Clean and prepare content for embedding."""
    if not content:
        return ""
        
    try:
        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Handle Unicode characters directly instead of using encode/decode
        content = content.replace('\\u2013', '–')  # Replace em-dash
        content = content.replace('\\u2014', '—')  # Replace en-dash
        content = content.replace('\\u2018', ''')  # Replace single quotes
        content = content.replace('\\u2019', ''')
        content = content.replace('\\u201C', '"')  # Replace double quotes
        content = content.replace('\\u201D', '"')
        
        # Add space after periods if missing
        content = re.sub(r'\.(?=[A-Z])', '. ', content)
        
        # Replace newlines with spaces
        content = content.replace('\n', ' ')
        
        # Remove any remaining control characters
        content = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)
        
        # Remove any remaining backslash escapes
        content = re.sub(r'\\[nrt]', ' ', content)
        
        # Normalize whitespace
        content = ' '.join(content.split())
        
        return content.strip()
        
    except Exception as e:
        print(f"Warning: Error cleaning content: {e}")
        return content.strip() if content else ""

def extract_thread_data(thread_data):
    """Extract and structure relevant data from thread API response for RAG ingestion."""
    thread = thread_data['thread']
    users = {user['id']: user for user in thread_data.get('users', [])}
    
    # Build the main content string that will be embedded
    content_parts = [
        f"Question: {clean_content(thread['title'])}",
        clean_content(thread['document'])
    ]
    
    # Add answers if they exist
    if thread['answers']:
        for answer in thread['answers']:
            answer_prefix = []
            # Add metadata about the answer
            if answer['is_endorsed']:
                answer_prefix.append("ENDORSED")
            user = users.get(answer['user_id'])
            if user and user.get('course_role') in ['admin', 'staff']:
                answer_prefix.append("STAFF RESPONSE")
            
            prefix_str = f"[{' | '.join(answer_prefix)}] " if answer_prefix else ""
            content_parts.append(f"\nAnswer: {prefix_str}{clean_content(answer['document'])}")
    
    # Combine all parts into a single string
    combined_content = "\n\n".join(content_parts)
    
    # Structure metadata for search context
    metadata = {
        'thread_id': thread['id'],
        'title': thread['title'],
        'created_at': thread['created_at'].split('+')[0],
        'is_answered': thread['is_answered'],
        'is_staff_answered': thread['is_staff_answered'],
        'category': thread['category'],
        'subcategory': thread['subcategory'],
        'answer_count': len(thread['answers']),
        'view_count': thread['view_count']
    }
    
    return {
        'content': combined_content,
        'metadata': metadata
    }

def send_to_chatbot(processed_threads):
    """Send processed threads to the chatbot API endpoint."""
    url = 'https://cse-360-rag-chatbot.vercel.app/api/ingest-batch'
    
    # Get API key from environment variables
    api_key = os.getenv('INGESTION_API_KEY')
    if not api_key:
        logger.error("INGESTION_API_KEY must be set in .env file")
        return None
    
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }
    
    try:
        response = requests.post(url, json=processed_threads, headers=headers)
        response.raise_for_status()
        print(f"\nSuccessfully sent {len(processed_threads)} threads to API")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to API: {e}")
        return None

def main():
    """Main execution function to fetch and process new Ed Discussion threads."""
    # Load credentials
    email = os.getenv('ED_EMAIL')
    password = os.getenv('ED_PASSWORD')
    
    if not email or not password:
        logger.error("ED_EMAIL and ED_PASSWORD must be set in .env file")
        return
    
    # Authentication
    login_result = check_login_type(email)
    if not login_result or login_result.get("type") != "password":
        logger.error("Login type check failed")
        return
    
    token_result = get_token(email, password)
    if not token_result or 'token' not in token_result:
        logger.error("Failed to obtain authentication token")
        return
    
    token = token_result['token']
    logger.info("Successfully authenticated")
    
    # Process threads
    processed_threads = []
    offset = 0
    limit = 30
    
    while True:
        url = f"https://us.edstem.org/api/courses/72657/threads?limit={limit}&offset={offset}&sort=new"
        logger.info(f"Fetching threads with offset {offset}...")
        
        try:
            response = requests.get(url, headers={'x-token': token, 'accept': 'application/json'})
            response.raise_for_status()
            data = response.json()
            
            if not data.get('threads'):
                break
            
            threads = data['threads']
            
            for thread in threads:
                logger.info(f"Processing thread {thread['id']}...")
                try:
                    thread_data = get_thread_data(token, thread['id'])
                    if thread_data:
                        processed_thread = extract_thread_data(thread_data)
                        processed_threads.append(processed_thread)
                except Exception as e:
                    logger.error(f"Error processing thread {thread['id']}: {e}")
            
            if len(threads) < limit:
                break
            
            offset += limit
            logger.info(f"Processed {len(processed_threads)} threads so far...")
            
        except Exception as e:
            logger.error(f"Error fetching threads: {e}")
            break
    
    # Send processed threads to API
    if processed_threads:
        result = send_to_chatbot(processed_threads)
        if result:
            logger.info(f"Successfully processed {len(processed_threads)} threads")
    else:
        logger.info("No threads to process")

if __name__ == "__main__":
    main()
