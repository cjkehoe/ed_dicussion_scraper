# Ed Discussion Scraper

A Python script to scrape questions and answers from Ed Discussion boards using AgentQL.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- On macOS/Linux:
```bash
source venv/bin/activate
```
- On Windows:
```bash
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the root directory with your Ed Discussion credentials:
```
ED_API_KEY=your_api_key_here
``` 