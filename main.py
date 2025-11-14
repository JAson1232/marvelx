import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import asyncio

from claim_processor import ClaimProcessor

# Initialize FastAPI app
app = FastAPI(
    title="Insurance Claim Processing System",
    description="LLM-based insurance claim evaluation using Google Gemini",
    version="1.0.0"
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount claim directories for serving images
for i in range(1, 26):
    claim_dir = Path(__file__).parent / f"claim {i}"
    if claim_dir.exists():
        app.mount(f"/claim-{i}", StaticFiles(directory=str(claim_dir)), name=f"claim_{i}")

# Initialize claim processor
claim_processor = None

@app.on_event("startup")
async def startup_event():
    """Initialize claim processor on startup."""
    global claim_processor
    try:
        claim_processor = ClaimProcessor()
        print("✓ Claim processor initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize claim processor: {str(e)}")
        print("  Please check your .env file and GOOGLE_API_KEY")

# Pydantic models
class ClaimSubmission(BaseModel):
    claim_numbers: List[int]
    enable_clinic_verification: Optional[bool] = False

class ClaimResponse(BaseModel):
    claim_number: int
    decision: str
    explanation: str
    confidence: Optional[float] = None
    timestamp: str

# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/past-runs", response_class=HTMLResponse)
async def past_runs(request: Request):
    """Serve the past runs page."""
    return templates.TemplateResponse("past_runs.html", {"request": request})

@app.get("/api/claims/available")
async def get_available_claims():
    """Get list of available claim numbers."""
    if not claim_processor:
        raise HTTPException(status_code=503, detail="Claim processor not initialized")
    
    try:
        claims = claim_processor.get_available_claims()
        return {
            "available_claims": claims,
            "total": len(claims)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/claims/{claim_number}/preview")
async def preview_claim(claim_number: int):
    """Get preview of a claim without processing."""
    if not claim_processor:
        raise HTTPException(status_code=503, detail="Claim processor not initialized")
    
    try:
        claim_data = claim_processor.load_claim_data(claim_number)
        
        # Convert image paths to base64 for preview
        images_preview = []
        for img in claim_data["images"]:
            with open(img["path"], "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
                images_preview.append({
                    "filename": img["filename"],
                    "data": f"data:image/{img['path'].split('.')[-1]};base64,{img_data}"
                })
        
        return {
            "claim_number": claim_number,
            "description": claim_data["description"],
            "documents": claim_data["documents"],
            "images": images_preview,
            "expected_answer": claim_data.get("expected_answer")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/claims/process")
async def process_claims(submission: ClaimSubmission):
    """Process one or more claims through the evaluation pipeline."""
    global claim_processor
    
    # Reinitialize processor with clinic verification setting
    enable_verification = submission.enable_clinic_verification
    claim_processor = ClaimProcessor(enable_clinic_verification=enable_verification)
    
    if not submission.claim_numbers:
        raise HTTPException(status_code=400, detail="No claims specified")
    
    try:
        # Process claims
        summary = await claim_processor.process_multiple_claims(submission.claim_numbers)
        
        # Add verification status to summary
        summary["clinic_verification_enabled"] = enable_verification
        
        return {
            "status": "completed",
            "summary": summary,
            "message": f"Successfully processed {len(submission.claim_numbers)} claims",
            "clinic_verification_used": enable_verification
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/claims/{claim_id}")
async def get_claim(claim_id: int):
    """Retrieve a specific claim's decision (from most recent results)."""
    if not claim_processor:
        raise HTTPException(status_code=503, detail="Claim processor not initialized")
    
    try:
        # Find most recent result for this claim
        results_dir = claim_processor.results_dir
        
        # Get all run directories sorted by timestamp (most recent first)
        run_dirs = sorted(
            [d for d in results_dir.iterdir() if d.is_dir()],
            key=lambda x: x.name,
            reverse=True
        )
        
        # Search for claim in most recent runs
        for run_dir in run_dirs:
            claim_file = run_dir / f"claim_{claim_id}.json"
            if claim_file.exists():
                with open(claim_file, 'r') as f:
                    return json.load(f)
        
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found in results")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/claims")
async def list_claims():
    """List all processed claims from most recent run."""
    if not claim_processor:
        raise HTTPException(status_code=503, detail="Claim processor not initialized")
    
    try:
        results_dir = claim_processor.results_dir
        
        # Get all run directories sorted by timestamp (most recent first)
        run_dirs = sorted(
            [d for d in results_dir.iterdir() if d.is_dir()],
            key=lambda x: x.name,
            reverse=True
        )
        
        if not run_dirs:
            return {"runs": [], "message": "No processed claims found"}
        
        # Get summaries from all runs
        runs = []
        for run_dir in run_dirs:
            summary_file = run_dir / "summary.json"
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                    runs.append({
                        "run_id": run_dir.name,
                        "timestamp": summary.get("run_timestamp"),
                        "claims_count": summary.get("statistics", {}).get("total_claims"),
                        "accuracy": summary.get("statistics", {}).get("accuracy"),
                        "statistics": summary.get("statistics")
                    })
        
        return {"runs": runs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results/{run_id}")
async def get_run_results(run_id: str):
    """Get detailed results for a specific run."""
    if not claim_processor:
        raise HTTPException(status_code=503, detail="Claim processor not initialized")
    
    try:
        run_dir = claim_processor.results_dir / run_id
        
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        summary_file = run_dir / "summary.json"
        if not summary_file.exists():
            raise HTTPException(status_code=404, detail=f"Summary not found for run {run_id}")
        
        with open(summary_file, 'r') as f:
            return json.load(f)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "processor_initialized": claim_processor is not None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("APP_PORT", 8000))
    host = os.getenv("APP_HOST", "0.0.0.0")
    
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║  Insurance Claim Processing System                         ║
    ║  LLM-powered claim evaluation with Google Gemini          ║
    ╚════════════════════════════════════════════════════════════╝
    
    🌐 Server starting on http://{host}:{port}
    📚 API docs available at http://{host}:{port}/docs
    
    """)
    
    uvicorn.run(app, host=host, port=port)
