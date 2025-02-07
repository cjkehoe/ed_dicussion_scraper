import os
from dotenv import load_dotenv
import agentql
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

# Configure AgentQL with API key
agentql.configure(api_key=os.getenv('AGENTQL_API_KEY'))

# Ed Discussion login URL
LOGIN_URL = "https://edstem.org/us/login"

def login_to_ed():
    playwright = sync_playwright().start()
    
    try:
        # Modified browser launch configuration - removed channel specification
        browser = playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        # Create a new context first
        context = browser.new_context()
        page = agentql.wrap(context.new_page())
        
        # Navigate to login page
        page.goto(LOGIN_URL)
        
        # Define email form query based on the JSON structure
        EMAIL_QUERY = """
        {
            email_input(input with class "start-input")
            continue_button(button with class "start-btn")
        }
        """
        
        # Get email form elements
        response = page.query_elements(EMAIL_QUERY)
        
        # Fill in email and click continue
        response.email_input.fill(os.getenv('ED_EMAIL'))
        response.continue_button.click()
        
        print("Clicked continue, waiting for password form...")
        # Add a small delay to ensure the password form is loaded
        page.wait_for_timeout(2000)  # 2 second delay
        
        # Wait for navigation after clicking continue
        page.wait_for_load_state('networkidle')

        print("Attempting to find password form elements...")
        # Define password form query
        PASSWORD_QUERY = """
        {
            password_input(input with class "start-input" and type "password")
            login_button(button with class "start-btn" and type "submit")
        }
        """

        try:
            # Get password form elements
            response = page.query_elements(PASSWORD_QUERY)
            
            if not hasattr(response, 'password_input') or not hasattr(response, 'login_button'):
                print("Failed to find password form elements!")
                print("Available elements:", vars(response))
                return None, None, None
            
            print("Found password form, attempting to fill and submit...")
            # Fill in password and click login
            response.password_input.fill(os.getenv('ED_PASSWORD'))
            
            print("Password entered, attempting to click login...")
            response.login_button.click()
            
            print("Login button clicked, waiting for navigation...")
            # Wait for navigation after login
            page.wait_for_load_state('networkidle')
            
            print("Attempting to find and click CSE 360 course...")
            # Define course selection query
            COURSE_QUERY = """
            {
                cse360_course(div with class "dash-course-code" and text "CSE 360 - Hybrid and Online - Spring 2025")
            }
            """
            
            try:
                # Get course element
                response = page.query_elements(COURSE_QUERY)
                
                if not hasattr(response, 'cse360_course'):
                    print("Failed to find CSE 360 course element!")
                    print("Available elements:", vars(response))
                    return None, None, None
                
                print("Found CSE 360 course, clicking...")
                response.cse360_course.click()
                
                # Wait for navigation after clicking course
                page.wait_for_load_state('networkidle')
                print("Successfully navigated to CSE 360 course page!")
                
                # Add a delay to keep the browser open
                page.wait_for_timeout(5000)  # 5 second delay
            
            except Exception as e:
                print(f"Failed to click course: {str(e)}")
                return None, None, None
                
            print("Navigation process completed!")
            
            return page, browser, playwright

        except Exception as e:
            print(f"Login failed: {str(e)}")
            if browser:
                browser.close()
            playwright.stop()
            return None, None, None

    except Exception as e:
        print(f"Login failed: {str(e)}")
        if browser:
            browser.close()
        playwright.stop()
        return None, None, None

if __name__ == "__main__":
    page, browser, playwright = login_to_ed()
    if page:
        browser.close()
        playwright.stop()  # Clean up playwright