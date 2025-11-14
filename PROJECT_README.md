# 🏥 Insurance Claim Processing System

An AI-powered insurance claim evaluation system using **Google Gemini 2.0 Flash** and **FastAPI**. This system automates the processing of insurance claims for the "Cancellation For Specific Reason" (CFSR) policy, analyzing documents and making APPROVE/DENY/UNCERTAIN decisions.

## ✨ Features

### Core Functionality
- **Web-Based UI**: Select individual claims (1-25) or process all at once
- **LLM-Powered Analysis**: Google Gemini 2.0 Flash for intelligent decision making
- **Multi-Language OCR**: Extract text from images in multiple languages (pytesseract)
- **Image Analysis**: Gemini Vision API for document metadata extraction
- **Fraud Detection**: Comprehensive checks for document authenticity
- **🔍 Clinic Verification**: Optional Google Search integration to verify medical facilities
- **Confidence Scoring**: Each decision includes confidence level
- **Timeline Analysis**: Intelligent medical condition duration vs travel date analysis
- **Results Storage**: Timestamped results with detailed breakdown
- **Performance Metrics**: Accuracy tracking against expected answers

## 📋 Prerequisites

- Python 3.11 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- Docker (optional, for containerized deployment)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd takehome-test-data

# Copy environment template
cp .env.example .env

# Edit .env and add your Google API key
# GOOGLE_API_KEY=your_actual_api_key_here
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install Tesseract OCR
# macOS:
brew install tesseract tesseract-lang

# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-spa tesseract-ocr-ita tesseract-ocr-deu

# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### 3. Run the Application

```bash
python main.py
```

The application will start on `http://localhost:8000`

### 4. Using the Web Interface

1. Open your browser to `http://localhost:8000`
2. Select claims to process (click individual claims or "Select All")
3. Click "Process Selected Claims"
4. View results with detailed analysis, extracted metadata, and accuracy metrics

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Docker Directly

```bash
# Build image
docker build -t claim-processor .

# Run container
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_api_key \
  -v $(pwd)/results:/app/results \
  claim-processor
```

## 📡 API Documentation

### Endpoints

#### `GET /`
Returns the web interface

#### `GET /api/claims/available`
Get list of available claims (1-25)

**Response:**
```json
{
  "available_claims": [1, 2, 3, ...],
  "total": 25
}
```

#### `GET /api/claims/{claim_number}/preview`
Preview claim details without processing

**Response:**
```json
{
  "claim_number": 1,
  "description": "...",
  "documents": [...],
  "images": [...],
  "expected_answer": {...}
}
```

#### `POST /api/claims/process`
Process selected claims through evaluation pipeline

**Request:**
```json
{
  "claim_numbers": [1, 2, 3]
}
```

**Response:**
```json
{
  "status": "completed",
  "summary": {
    "run_timestamp": "20241109_143022",
    "claims_processed": [1, 2, 3],
    "statistics": {
      "total_claims": 3,
      "approved": 1,
      "denied": 2,
      "uncertain": 0,
      "exact_matches": 2,
      "accuracy": 0.87
    },
    "results": [...]
  }
}
```

#### `GET /api/claims/{claim_id}`
Get decision for specific claim from most recent run

#### `GET /api/claims`
List all previous processing runs with statistics

#### `GET /api/results/{run_id}`
Get detailed results for a specific run

#### `GET /health`
Health check endpoint

Interactive API documentation available at `http://localhost:8000/docs`

## 📊 Results Structure

Results are saved in timestamped folders:

```
results/
├── run_20241109_143022_3_claims/
│   ├── summary.json           # Run statistics and overview
│   ├── claim_1.json          # Detailed result for claim 1
│   ├── claim_2.json          # Detailed result for claim 2
│   └── claim_3.json          # Detailed result for claim 3
└── run_20241109_150445_25_claims/
    ├── summary.json
    ├── claim_1.json
    ├── ...
    └── claim_25.json
```

### Result File Structure

Each claim result includes:

```json
{
  "claim_number": 1,
  "timestamp": "2024-11-09T14:30:22",
  "claim_data": {
    "description": "Customer's claim description",
    "documents": [...]
  },
  "image_metadata": [
    {
      "filename": "medical_certificate.jpg",
      "metadata": {
        "document_type": "medical certificate",
        "key_information": {
          "names": ["John Doe"],
          "dates": ["2024-10-15"],
          "amounts": [],
          "locations": ["City Hospital"]
        },
        "text_content": "Extracted text...",
        "authenticity_indicators": {
          "has_signature": true,
          "has_official_stamp": true,
          "has_letterhead": true,
          "quality_assessment": "High quality scan"
        },
        "fraud_concerns": [],
        "language": "English"
      }
    }
  ],
  "llm_decision": {
    "decision": "APPROVE",
    "explanation": "Valid medical certificate with proper documentation",
    "confidence": 0.95,
    "policy_section": "Trip Cancellation - Medical Emergency",
    "fraud_indicators": [],
    "required_documents": ["medical certificate", "booking proof"],
    "missing_documents": [],
    "compensation_amount": "€500",
    "reasoning_steps": [
      "Verified medical certificate authenticity",
      "Confirmed signature and stamp present",
      "Dates align with travel schedule",
      "No fraud indicators detected"
    ]
  },
  "expected_answer": {
    "decision": "APPROVE"
  },
  "matches_expected": {
    "exact_match": true,
    "acceptable_match": false,
    "expected": "APPROVE",
    "actual": "APPROVE"
  }
}
```

## 🧠 System Architecture

### Decision-Making Process

1. **Data Loading**: Load claim description, supporting documents, and images
2. **Image Analysis**: 
   - Extract metadata using Gemini Vision API
   - Perform OCR with Tesseract (multilingual support)
   - Detect authenticity indicators (signatures, stamps, letterhead)
3. **LLM Evaluation**: 
   - Feed system prompt, policy rules, and claim data to Gemini
   - Apply fraud detection rules
   - Generate decision with reasoning
4. **Validation**: Compare with expected answers for accuracy tracking
5. **Storage**: Save detailed results with timestamp

### System Prompt Engineering

The system prompt is defined in `system_prompt.toml` and includes:

- **Policy Coverage Rules**: Trip cancellation, personal effects, missed departures
- **Exclusion Criteria**: What's not covered
- **Document Validation**: Strict rules for medical certificates, police reports, etc.
- **Fraud Detection**: Patterns to identify suspicious documents
- **Decision Guidelines**: When to APPROVE, DENY, or mark as UNCERTAIN
- **Examples**: Based on actual answer.json patterns from training data

### Key Validation Rules

**Medical Certificates MUST have:**
- Official document (not text description)
- Visible signature from medical professional
- Official stamps or letterhead
- Patient name matching claimant
- Medical condition preventing travel
- Consistent dates

**Fraud Indicators:**
- Photoshopped signatures or stamps
- Inconsistent dates or formatting
- Name redactions or mismatches
- Documents stating patient is healthy
- Missing required signatures
- Suspicious date alterations

## 🎯 Performance

Based on the benchmark dataset of 25 claims:

- **Decision Distribution**: 36% Approve, 48% Deny, 16% Uncertain
- **Accuracy Target**: >85% exact or acceptable matches
- **Processing Time**: ~10-15 seconds per claim (depending on images)

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.11)
- **LLM**: Google Gemini 2.0 Flash
- **Document Processing**: 
  - Google Gemini Vision API
  - Tesseract OCR
  - Pillow (PIL)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Configuration**: TOML
- **Containerization**: Docker, Docker Compose

## 📝 Configuration

### Environment Variables

Create a `.env` file:

```env
# Required
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Optional
APP_HOST=0.0.0.0
APP_PORT=8000
```

### System Prompt Customization

Edit `system_prompt.toml` to adjust:
- Policy coverage rules
- Validation requirements
- Fraud detection patterns
- Decision thresholds

## 🧪 Testing

Process all 25 benchmark claims:

```bash
# Through web interface: Click "Select All 25 Claims" → "Process"

# Or via API:
curl -X POST http://localhost:8000/api/claims/process \
  -H "Content-Type: application/json" \
  -d '{"claim_numbers": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25]}'
```

## 🐛 Troubleshooting

### "GOOGLE_API_KEY not found"
- Ensure `.env` file exists and contains your API key
- Restart the application after adding the key

### Tesseract OCR errors
- Install Tesseract and language packs
- Verify installation: `tesseract --version`

### Image processing failures
- Check image formats are supported (PNG, JPG, WEBP)
- Verify images are not corrupted

### Docker issues
- Ensure Docker daemon is running
- Check port 8000 is not in use: `lsof -i :8000`

## 📄 Project Structure

```
takehome-test-data/
├── main.py                  # FastAPI application
├── claim_processor.py       # Core claim processing logic
├── system_prompt.toml       # LLM system prompt configuration
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker compose configuration
├── .env                    # Environment variables (create from .env.example)
├── .env.example           # Environment template
├── templates/
│   └── index.html         # Web interface
├── static/
│   ├── style.css          # Styles
│   └── script.js          # Frontend logic
├── results/               # Processing results (created at runtime)
├── claim 1/ through claim 25/  # Test data
├── policy.md              # Insurance policy documentation
└── README.md             # This file
```

## 🎓 Implementation Notes

### Approach

1. **Comprehensive System Prompt**: Created detailed TOML-based prompt incorporating all policy rules and validation patterns from the 25 answer.json examples
2. **Dual Document Processing**: Combined Gemini Vision API for intelligent document understanding with OCR for text extraction
3. **Fraud Detection**: Implemented pattern matching based on actual fraud indicators from training data
4. **Results Management**: Timestamped folders preserve all runs for comparison and analysis
5. **Modern Web UI**: Clean, responsive interface for easy claim selection and result visualization

### Assumptions

- Medical certificates must be official documents (not text descriptions)
- Signatures and stamps are required for medical documentation
- Future events (flights weeks away) should be marked UNCERTAIN
- Date inconsistencies are strong fraud indicators
- Multilingual support required for EU claims

## 📮 Author

Created for the MarvelX Take-Home Assignment

## 📜 License

This project is for evaluation purposes.

---

**Ready to process claims?** Start the application and open `http://localhost:8000`! 🚀
