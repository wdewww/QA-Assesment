# QA Assessment Tool

A FastAPI-based web application that analyzes websites across multiple quality dimensions including performance, security, technical aspects, and user experience using AI-powered analysis.

## Features

- **Multi-dimensional QA Analysis**: Performance, Security, Technical, and UX assessments
- **AI-Powered**: Leverages Google's Gemini API for intelligent insights
- **Automated Reports**: Generates comprehensive PDF reports
- **Web Scraping**: Uses Playwright for reliable page fetching 
- **REST API**: Easy-to-use API endpoints

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager (for local setup)
- Docker and Docker Compose (for containerized setup)
- Google Gemini API key

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd QA-Assesment
```

### 2. Configure Environment Variables

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and replace `your_gemini_api_key_here` with your actual Gemini API key.

> **Note**: Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

## Running Locally with uv

### Installation

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
uv sync
```

3. Install Playwright browsers:
```bash
uv playwright install chromium
uv playwright install-deps chromium
```

### Run the Application

```bash
cd app
uv run fastapi dev
```

The application will be available at `http://localhost:8000`

## Running with Docker

### Using Docker (Recommended)

1. Make sure you have Docker  installed

2.  Build the image:
```bash
docker build -t qa-analyzer .
```

3. Run the container:
```bash
docker run -p 8000:8000 --env-file .env -v ./reports:/app/reports qa-analyzer
```