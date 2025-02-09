import os
from dotenv import load_dotenv
import agentql
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

# Configure AgentQL with API key
agentql.configure(api_key=os.getenv('AGENTQL_API_KEY'))

# Constants
LOGIN_URL = "https://edstem.org/us/login"
API_BASE_URL = "https://us.edstem.org/api"

def get_all_thread_links(page, course_id="72657"):
    """
    Get all thread links using Ed's API endpoint directly.
    
    Args:
        page: Playwright page object with active session
        course_id (str): Ed Discussion course ID
        
    Returns:
        list: List of thread URLs, or None if failed
    """
    print("Collecting all thread links...")
    
    # Get authentication token
    token = page.evaluate("""() => {
        return localStorage.getItem('authToken') || localStorage.getItem('authToken:us');
    }""")
    
    if not token:
        print("Failed to get authentication token")
        return None
    
    headers = {
        'x-token': token,
        'accept': 'application/json',
    }
    
    all_threads = []
    offset = 0
    limit = 30
    
    while True:
        url = f"{API_BASE_URL}/courses/{course_id}/threads?limit={limit}&offset={offset}&sort=new"
        print(f"Fetching threads with offset {offset}...")
        
        try:
            response = page.request.get(url, headers=headers)
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

def login_to_ed():
    """
    Log into Ed Discussion and navigate to the CSE 360 course page.
    
    Returns:
        tuple: (page, browser, playwright, thread_links) or (None, None, None, None) if failed
    """
    playwright = sync_playwright().start()
    
    try:
        browser = playwright.chromium.launch(
            headless=False,
            args=['--disable-dev-shm-usage', '--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context = browser.new_context()
        page = agentql.wrap(context.new_page())
        
        # Login process
        page.goto(LOGIN_URL)
        
        # Email form
        email_query = """
        {
            email_input(input with class "start-input")
            continue_button(button with class "start-btn")
        }
        """
        response = page.query_elements(email_query)
        response.email_input.fill(os.getenv('ED_EMAIL'))
        response.continue_button.click()
        
        # Wait for password form
        page.wait_for_timeout(2000)
        page.wait_for_load_state('networkidle')
        
        # Password form
        password_query = """
        {
            password_input(input with class "start-input" and type "password")
            login_button(button with class "start-btn" and type "submit")
        }
        """
        response = page.query_elements(password_query)
        response.password_input.fill(os.getenv('ED_PASSWORD'))
        response.login_button.click()
        
        # Wait for navigation and find course
        page.wait_for_load_state('networkidle')
        course_query = """
        {
            cse360_course(div with class "dash-course-code" and text "CSE 360 - Hybrid and Online - Spring 2025")
        }
        """
        response = page.query_elements(course_query)
        response.cse360_course.click()
        
        # Wait for course page to load
        page.wait_for_load_state('networkidle')
        
        # Get all thread links
        thread_links = get_all_thread_links(page)
        if not thread_links:
            return None, None, None, None
            
        return page, browser, playwright, thread_links

    except Exception as e:
        print(f"Login failed: {str(e)}")
        if browser:
            browser.close()
        playwright.stop()
        return None, None, None, None

def get_thread_data(page, thread_id):
    """
    Fetch detailed data for a specific thread using Ed's API endpoint.
    
    Args:
        page: Playwright page object with active session
        thread_id (str): Thread ID to fetch
        
    Returns:
        dict: Thread data, or None if failed
    """
    print(f"Fetching data for thread {thread_id}...")
    
    # Get authentication token
    token = page.evaluate("""() => {
        return localStorage.getItem('authToken') || localStorage.getItem('authToken:us');
    }""")
    
    if not token:
        print("Failed to get authentication token")
        return None
    
    headers = {
        'x-token': token,
        'accept': 'application/json',
    }
    
    url = f"{API_BASE_URL}/threads/{thread_id}?view=1"
    
    try:
        response = page.request.get(url, headers=headers)
        thread_data = response.json()
        return thread_data
        
    except Exception as e:
        print(f"Error fetching thread data: {str(e)}")
        return None

def extract_thread_data(thread_data):
    """
    Extract relevant data from thread API response.
    
    Args:
        thread_data (dict): Raw API response
        
    Returns:
        dict: Structured thread data
    """
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
    """Main execution function."""
    page, browser, playwright, thread_links = login_to_ed()
    try:
        if thread_links:
            print("\nCollecting thread data...")
            all_thread_data = []
            
            for link in thread_links:
                thread_id = link.split('/')[-1]
                thread_data = get_thread_data(page, thread_id)
                if thread_data:
                    structured_data = extract_thread_data(thread_data)
                    all_thread_data.append(structured_data)
                    print(f"Collected data for thread {thread_id}")
            
            print(f"\nTotal threads processed: {len(all_thread_data)}")
            # TODO: Save to vector database
                
    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

if __name__ == "__main__":
    main()