# Insurance Claim Processing System

An AI-powered insurance claim evaluation system for processing travel insurance claims using Google Gemini 2.0 Flash LLM with vision capabilities.

## Overview

This system evaluates insurance claims for the "Cancellation For Specific Reason" (CFSR) policy, determining whether claims should be APPROVED, DENIED, or marked as UNCERTAIN. The system uses advanced AI to analyze medical certificates, booking confirmations, and other supporting documents to detect fraud and validate claim legitimacy.

## Features

- **AI-Powered Analysis**: Uses Google Gemini 2.0 Flash with vision capabilities to analyze documents
- **Fraud Detection**: Advanced fraud detection including visual document analysis, temporal logic validation, and name verification
- **Multi-Format Support**: Processes images (JPG, PNG, WebP), text documents, and structured data
- **Web Interface**: FastAPI-based web application with HTML templates
- **Batch Processing**: Process multiple claims with configurable delays to respect API limits
- **Results Dashboard**: View past processing runs with detailed claim analysis
- **Docker Support**: Containerized deployment for easy setup

## Architecture

- **Backend**: FastAPI (Python)
- **AI Model**: Google Gemini 2.0 Flash
- **Frontend**: HTML/JavaScript with Jinja2 templates
- **OCR**: Tesseract for text extraction from images
- **Optional**: Google Search API for clinic verification
- **Deployment**: Docker Compose

## Prerequisites

- Docker and Docker Compose
- Google Cloud API Key with Gemini API access
- (Optional) Google Custom Search API credentials for clinic verification

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/JAson1232/marvelx.git
cd marvelx
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# Required: Google Gemini API Key
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Optional: Google Search API for clinic verification
GOOGLE_SEARCH_API_KEY=your_google_search_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_custom_search_engine_id_here
```

### 3. Build and Run with Docker

```bash
# Build and start the application
docker compose up -d

# View logs
docker compose logs -f

# Stop the application
docker compose down
```

The application will be available at `http://localhost:8000`

## Usage

### Web Interface

1. **Home Page** (`/`): Select and process individual claims
2. **Past Runs** (`/past-runs`): View results from previous processing runs

### API Endpoints

- `GET /api/claims/available` - List available claims
- `POST /api/claims/process` - Process selected claims
- `GET /api/results/{run_id}` - Get results for a specific run

### Processing Claims

1. Select claims from the available list
2. Click "Process Claims" to start AI analysis
3. View results in the "Past Runs" section
4. Click on individual claims to see detailed analysis with images

## Approach & Assumptions

### AI-Powered Claim Evaluation

The system uses a structured prompt engineering approach with Google Gemini 2.0 Flash to evaluate claims based on:

- **Policy Coverage Analysis**: Strict adherence to CFSR policy rules
- **Document Validation**: Multi-layered validation of medical certificates, bookings, and supporting documents
- **Fraud Detection**: Hierarchical fraud detection with priority-based checks
- **Timeline Analysis**: Medical condition severity vs. travel date logic
- **Name Verification**: Cross-document name consistency validation

### Key Assumptions

1. **Document Authenticity**: Medical certificates are official documents (not text descriptions)
2. **Image Quality**: Documents are provided as clear, readable images
3. **Policy Strictness**: Claims must meet ALL policy requirements for approval
4. **Fraud Prevention**: Conservative approach - prefer UNCERTAIN over incorrect APPROVE
5. **Medical Expertise**: AI provides medical claim evaluation, not medical diagnosis

### Processing Logic

1. **File Type Validation**: Reject non-image medical documents immediately
2. **Document Analysis**: Extract text, dates, names, and authenticity indicators
3. **Fraud Priority Checks**: Apply hierarchical fraud detection (Priority 1 = automatic deny)
4. **Timeline Assessment**: Evaluate medical condition severity vs. travel timing
5. **Decision Making**: APPROVE/DENY/UNCERTAIN with detailed reasoning

### Fraud Detection Hierarchy

- **Priority 1 (Auto-Deny)**: File format issues, temporal impossibilities, health contradictions
- **Priority 2 (Strong Deny/UNCERTAIN)**: Missing signatures, visual manipulation, major inconsistencies
- **Priority 3 (UNCERTAIN)**: Future timeline uncertainty, minor issues, unclear handwriting

## Configuration

### System Prompt

The AI behavior is controlled by `system_prompt.toml` which includes:
- Policy coverage definitions
- Document validation rules
- Fraud detection checklists
- Decision guidelines
- Output format specifications

### Claim Data Structure

Each claim folder contains:
- `description.txt` - Claim narrative
- `answer.json` - Expected decision (for testing)
- Supporting documents (images, markdown files)
- Booking confirmations and other evidence

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY=your_key_here

# Run the application
python main.py
```

## API Rate Limiting

The system includes configurable delays between claim processing to respect API limits:
- Default: 30 seconds between claims
- Configurable in `claim_processor.py`

## Security Considerations

- API keys stored securely in environment variables
- No sensitive data persisted in application logs
- Input validation on all API endpoints
- Containerized deployment for isolation

## Troubleshooting

### Common Issues

1. **"GOOGLE_API_KEY not found"**: Ensure `.env` file exists with correct API key
2. **"Failed to initialize claim processor"**: Check TOML syntax in `system_prompt.toml`
3. **"Clinic verification disabled"**: Missing optional Google Search API credentials

### Logs

```bash
# View application logs
docker compose logs claim-processor

# View with follow
docker compose logs -f claim-processor
```

## License

This project is part of a technical assessment and is not licensed for production use. Otherwise, enjoy :) </content>
