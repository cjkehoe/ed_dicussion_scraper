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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True in production
        page = agentql.wrap(browser.new_page())
        
        try:
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
            
            # Wait for navigation after clicking continue
            page.wait_for_load_state('networkidle')
            
            print("Email submitted! Please check your email for the magic link.")
            print("The browser will stay open for 60 seconds to allow you to complete the login.")
            
            # Keep the browser open for manual magic link login
            page.wait_for_timeout(60000)  # 60 seconds
            
            return page, browser
            
        except Exception as e:
            print(f"Login failed: {str(e)}")
            browser.close()
            return None, None

if __name__ == "__main__":
    page, browser = login_to_ed()
    if page:
        browser.close()