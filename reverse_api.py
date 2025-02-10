import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables at the start
load_dotenv()

def check_login_type(email):
    # API endpoint
    url = "https://us.edstem.org/api/login_type"
    
    # Headers to mimic browser request
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://edstem.org',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
    }
    
    # Request payload
    payload = {
        "login": email,
        "force_code": False,
        "force_reauth": False
    }
    
    try:
        # Make POST request
        response = requests.post(url, headers=headers, json=payload)
        
        # Print detailed response information
        print("\nResponse Status Code:", response.status_code)
        print("\nResponse Headers:")
        for header, value in response.headers.items():
            print(f"{header}: {value}")
        print("\nRaw Response Content:")
        print(response.text)
        print("\nParsed JSON Response:")
        
        # Check if request was successful
        response.raise_for_status()
        
        # Return the JSON response
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

def get_token(email, password):
    # API endpoint
    url = "https://us.edstem.org/api/token"
    
    # Headers remain the same as check_login_type
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://edstem.org',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
    }
    
    # Request payload for token
    payload = {
        "login": email,
        "password": password
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        # Print detailed response information
        print("\nToken Request Status Code:", response.status_code)
        print("\nResponse Headers:")
        for header, value in response.headers.items():
            print(f"{header}: {value}")
        print("\nRaw Response Content:")
        print(response.text)
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error occurred during token request: {e}")
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

def extract_thread_data(thread_data):
    """Extract relevant data from thread API response."""
    thread = thread_data['thread']
    
    # Extract answers
    answers = []
    for answer in thread.get('answers', []):
        answers.append({
            'id': answer['id'],
            'content': answer['document'],
            'is_endorsed': answer['is_endorsed'],
            'created_at': answer['created_at'],
            'is_staff_answered': thread['is_staff_answered']
        })
    
    # Structure thread data
    return {
        'id': thread['id'],
        'title': thread['title'],
        'content': thread['document'],
        'type': thread['type'],
        'category': thread['category'],
        'created_at': thread['created_at'],
        'is_answered': thread['is_answered'],
        'is_staff_answered': thread['is_staff_answered'],
        'answers': answers
    }

def main():
    """Main execution function using environment variables for authentication."""
    email = os.getenv('ED_EMAIL')
    password = os.getenv('ED_PASSWORD')
    
    if not email or not password:
        print("Error: ED_EMAIL and ED_PASSWORD must be set in .env file")
        return
        
    login_result = check_login_type(email)
    
    if login_result and login_result.get("type") == "password":
        token_result = get_token(email, password)
        
        if token_result and 'token' in token_result:
            token = token_result['token']
            print("\nSuccessfully obtained token!")
            
            # Get all thread links
            thread_links = get_all_thread_links(token)
            
            if thread_links:
                print("\nCollecting thread data...")
                all_thread_data = []
                
                for link in thread_links:
                    thread_id = link.split('/')[-1]
                    thread_data = get_thread_data(token, thread_id)
                    if thread_data:
                        structured_data = extract_thread_data(thread_data)
                        all_thread_data.append(structured_data)
                        print(f"Collected data for thread {thread_id}")
                
                print(f"\nTotal threads processed: {len(all_thread_data)}")
                # Save data or process further as needed
                
                # Example: Print first thread data
                if all_thread_data:
                    print("\nFirst thread data sample:")
                    print(json.dumps(all_thread_data[0], indent=2))

if __name__ == "__main__":
    main()
