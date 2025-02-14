import os
import requests
import json
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def clean_content(content):
    """Clean and prepare content from PDF for embedding."""
    if not content:
        return ""
    
    try:
        # Remove excessive whitespace and newlines
        content = re.sub(r'\s+', ' ', content)
        
        # Remove any control characters
        content = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)
        
        return content.strip()
        
    except Exception as e:
        logger.error(f"Error cleaning content: {e}")
        return content.strip() if content else ""

def determine_assignment_type(filename):
    """Determine assignment type based on filename or content."""
    filename = filename.lower()
    if 'homework' in filename or 'hw' in filename:
        return 'homework'
    elif 'project' in filename:
        return 'project'
    elif 'syllabus' in filename:
        return 'syllabus'
    else:
        return 'other'

def process_pdf(file_path):
    """Process a single PDF file and extract its content with metadata."""
    try:
        reader = PdfReader(file_path)
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        
        # Combine all pages into one document
        all_content = []
        total_pages = len(reader.pages)
        
        for page_num, page in enumerate(reader.pages, 1):
            content = page.extract_text()
            cleaned_content = clean_content(content)
            if cleaned_content:
                all_content.append(cleaned_content)
        
        if not all_content:
            return None
            
        # Create single document with all pages
        return [{
            'content': '\n\n'.join(all_content),
            'metadata': {
                'document_id': base_name,
                'title': base_name,
                'created_at': datetime.now().isoformat(),
                'section': 'instructions',
                'assignment_type': determine_assignment_type(filename),
                'total_pages': total_pages
            }
        }]
        
    except Exception as e:
        logger.error(f"Error processing PDF {file_path}: {e}")
        return None

def send_to_api(processed_documents):
    """Send processed documents to the API endpoint."""
    url = 'http://localhost:3000/api/ingest-instructions'
    
    api_key = os.getenv('INGESTION_API_KEY')
    if not api_key:
        logger.error("INGESTION_API_KEY must be set in .env file")
        return None
    
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }
    
    try:
        response = requests.post(url, json=processed_documents, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully sent {len(processed_documents)} documents to API")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending data to API: {e}")
        return None

def main():
    """Main execution function to process PDFs and send to API."""
    pdf_directory = 'pdfs'
    
    if not os.path.exists(pdf_directory):
        logger.error(f"Directory {pdf_directory} does not exist")
        return
    
    all_processed_documents = []
    
    # Process each PDF in the directory
    for filename in os.listdir(pdf_directory):
        if filename.lower().endswith('.pdf'):
            file_path = os.path.join(pdf_directory, filename)
            logger.info(f"Processing {filename}...")
            
            processed_pages = process_pdf(file_path)
            if processed_pages:
                all_processed_documents.extend(processed_pages)
    
    # Send to API if we have processed documents
    if all_processed_documents:
        result = send_to_api(all_processed_documents)
        if result:
            logger.info(f"Successfully processed {len(all_processed_documents)} pages from PDFs")
    else:
        logger.info("No documents to process")

if __name__ == "__main__":
    main() 