import os
import json
import toml
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image
import pytesseract
from google_search_tool import GoogleSearchTool

# Load environment variables
load_dotenv()

class ClaimProcessor:
    def __init__(self, enable_clinic_verification: bool = False):
        # Configure Gemini API
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # Set up genai client with API key
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.0-flash-exp"
        
        # Initialize Google Search Tool
        self.search_tool = GoogleSearchTool()
        self.enable_clinic_verification = enable_clinic_verification and self.search_tool.enabled
        
        if enable_clinic_verification and not self.search_tool.enabled:
            print("⚠️  Clinic verification requested but Google Search API not configured")
        
        # Load system prompt from TOML
        self.system_prompt = self._load_system_prompt()
        
        # Base directory for claims
        self.base_dir = Path(__file__).parent
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
    
    def _load_system_prompt(self) -> str:
        """Load and format system prompt from TOML file."""
        prompt_file = Path(__file__).parent / "system_prompt.toml"
        prompt_config = toml.load(prompt_file)
        
        # Build comprehensive system prompt
        prompt_parts = []
        
        # Main instructions
        prompt_parts.append(prompt_config['system_prompt']['main_instructions'])
        
        # Policy coverage
        prompt_parts.append("\n## POLICY COVERAGE\n")
        for key, value in prompt_config['policy']['coverage'].items():
            prompt_parts.append(f"\n### {key.replace('_', ' ').title()}\n{value}")
        
        # Exclusions
        prompt_parts.append("\n## POLICY EXCLUSIONS\n")
        prompt_parts.append(prompt_config['policy']['exclusions']['not_covered'])
        
        # Document validation
        prompt_parts.append("\n## DOCUMENT VALIDATION RULES\n")
        for key, value in prompt_config['document_validation'].items():
            prompt_parts.append(f"\n### {key.replace('_', ' ').title()}\n{value}")
        
        # Fraud priority hierarchy
        prompt_parts.append("\n## FRAUD DETECTION PRIORITY HIERARCHY\n")
        prompt_parts.append(prompt_config['fraud_priority']['detection_hierarchy'])
        
        # Decision guidelines
        prompt_parts.append("\n## DECISION GUIDELINES\n")
        for key, value in prompt_config['decision_guidelines'].items():
            prompt_parts.append(f"\n### {key.upper()}\n{value}")
        
        # Output format
        prompt_parts.append("\n## OUTPUT FORMAT\n")
        prompt_parts.append(prompt_config['output_format']['structure'])
        
        return "\n".join(prompt_parts)
    
    def get_available_claims(self) -> List[int]:
        """Get list of available claim numbers."""
        claims = []
        for i in range(1, 26):
            claim_dir = self.base_dir / f"claim {i}"
            if claim_dir.exists():
                claims.append(i)
        return sorted(claims)
    
    def load_claim_data(self, claim_number: int) -> Dict:
        """Load all data for a specific claim."""
        claim_dir = self.base_dir / f"claim {claim_number}"
        
        if not claim_dir.exists():
            raise ValueError(f"Claim {claim_number} not found")
        
        claim_data = {
            "claim_number": claim_number,
            "description": None,
            "documents": [],
            "images": [],
            "expected_answer": None
        }
        
        # Load description
        desc_file = claim_dir / "description.txt"
        if desc_file.exists():
            claim_data["description"] = desc_file.read_text()
        
        # Load expected answer
        answer_file = claim_dir / "answer.json"
        if answer_file.exists():
            claim_data["expected_answer"] = json.loads(answer_file.read_text())
        
        # Load supporting documents
        for file in claim_dir.iterdir():
            if file.is_file():
                if file.suffix == ".md" and file.name != "answer.json":
                    claim_data["documents"].append({
                        "filename": file.name,
                        "content": file.read_text(),
                        "type": "markdown"
                    })
                elif file.suffix in [".png", ".jpg", ".jpeg", ".webp"]:
                    claim_data["images"].append({
                        "filename": file.name,
                        "path": str(file),
                        "type": "image"
                    })
        
        return claim_data
    
    def extract_text_with_ocr(self, image_path: str) -> Dict:
        """Extract text from image using Tesseract OCR."""
        try:
            # Open image
            img = Image.open(image_path)
            
            # Try different languages based on file name hints
            languages = ['eng']  # Default to English
            
            # Add other languages based on filename
            path_lower = image_path.lower()
            if 'french' in path_lower or 'french' in path_lower:
                languages.append('fra')
            if 'spanish' in path_lower or 'spanish' in path_lower:
                languages.append('spa')
            if 'italian' in path_lower or 'italian' in path_lower:
                languages.append('ita')
            if 'german' in path_lower or 'german' in path_lower:
                languages.append('deu')
            if 'belgian' in path_lower:
                languages.extend(['fra', 'nld'])
            
            # Perform OCR
            lang_string = '+'.join(languages)
            ocr_text = pytesseract.image_to_string(img, lang=lang_string)
            
            # Get additional data
            ocr_data = pytesseract.image_to_data(img, lang=lang_string, output_type=pytesseract.Output.DICT)
            
            # Calculate confidence
            confidences = [int(conf) for conf in ocr_data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": ocr_text.strip(),
                "confidence": avg_confidence,
                "languages_used": languages,
                "word_count": len(ocr_text.split()),
                "success": True
            }
            
        except Exception as e:
            return {
                "text": "",
                "error": f"OCR failed: {str(e)}",
                "success": False
            }
    
    async def extract_image_metadata(self, image_path: str) -> Dict:
        """Extract metadata and content from images using Gemini Vision and OCR."""
        try:
            # First, run OCR
            print(f"    Running OCR on image...")
            ocr_result = self.extract_text_with_ocr(image_path)
            
            # Read image file as bytes
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Create prompt for metadata extraction
            extraction_prompt = """
            Analyze this document image and extract the following information in JSON format:
            {
                "document_type": "type of document (e.g., medical certificate, boarding pass, receipt)",
                "key_information": {
                    "names": ["any names found"],
                    "dates": ["any dates found"],
                    "amounts": ["any monetary amounts"],
                    "locations": ["any locations mentioned"],
                    "organizations": ["hospitals, airlines, etc."]
                },
                "text_content": "full text transcription of the document",
                "authenticity_indicators": {
                    "has_signature": true/false,
                    "has_official_stamp": true/false,
                    "has_letterhead": true/false,
                    "quality_assessment": "description of document quality"
                },
                "fraud_concerns": ["any suspicious elements noticed"],
                "language": "primary language of document"
            }
            
            Be thorough and precise. Extract all visible text.
            """
            
            # Use the new genai client API with image
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    extraction_prompt,
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/jpeg",
                            data=image_bytes
                        )
                    )
                ]
            )
            
            # Parse JSON response
            try:
                # Try to extract JSON from response
                response_text = response.text
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                metadata = json.loads(response_text.strip())
            except:
                metadata = {
                    "raw_response": response.text,
                    "extraction_error": "Could not parse structured metadata"
                }
            
            # Add OCR results to metadata
            metadata["ocr_extraction"] = ocr_result
            
            return metadata
            
        except Exception as e:
            return {"error": f"Failed to extract metadata: {str(e)}"}
    
    async def process_claim(self, claim_number: int) -> Dict:
        """Process a single claim and return decision."""
        print(f"Processing claim {claim_number}...")
        
        # Load claim data
        claim_data = self.load_claim_data(claim_number)
        
        # Extract metadata from images
        image_metadata = []
        for img in claim_data["images"]:
            print(f"  Extracting metadata from {img['filename']}...")
            metadata = await self.extract_image_metadata(img["path"])
            image_metadata.append({
                "filename": img["filename"],
                "metadata": metadata
            })
        
        # Build claim analysis prompt
        analysis_prompt = self._build_analysis_prompt(claim_data, image_metadata)
        
        # Prepare content parts with text and images
        content_parts = [analysis_prompt]
        
        # Add images as Parts with proper Blob format
        for img in claim_data["images"]:
            with open(img["path"], 'rb') as f:
                image_bytes = f.read()
            # Determine mime type from file extension
            ext = Path(img["path"]).suffix.lower()
            mime_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp'
            }
            mime_type = mime_map.get(ext, 'image/jpeg')
            content_parts.append(
                types.Part(
                    inline_data=types.Blob(
                        mime_type=mime_type,
                        data=image_bytes
                    )
                )
            )
        
        # Get decision from Gemini using two-step approach for clinic verification
        print(f"  Analyzing claim with LLM...")
        
        # Configure generation settings
        config = {
            "temperature": 0.3,
            "max_output_tokens": 4096,
        }
        
        # TWO-STEP APPROACH: Google Search doesn't work with multimodal (images)
        # Step 1: Always analyze documents with images first
        print("  � Step 1: Analyzing documents and images...")
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=content_parts,
            config=types.GenerateContentConfig(**config)
        )
        initial_analysis = response.text
        
        # Step 2: If clinic verification enabled, do text-only verification with Google Search
        final_response_text = initial_analysis
        final_response = None
        grounding_metadata = []
        
        if self.enable_clinic_verification:
            print("  🔍 Step 2: Verifying medical facilities with Google Search...")
            
            verification_prompt = f"""
{self.system_prompt}

## INITIAL DOCUMENT ANALYSIS
Below is the initial analysis of the claim with all documents and images:

{initial_analysis}

## CLINIC VERIFICATION TASK
You now have access to Google Search to verify medical facilities.

⚠️ CRITICAL: DO NOT MAKE UP OR FABRICATE FACILITY NAMES
- ONLY search for facilities that are EXPLICITLY and CLEARLY mentioned in the documents above
- If you cannot extract a SPECIFIC facility name, DO NOT attempt to search
- DO NOT guess, infer, or create facility names
- If no clear facility name exists, skip verification and keep your original decision

Your task:
1. Review the initial analysis - are there SPECIFIC medical facility names mentioned?
2. If YES and the name is CLEAR:
   - Use Google Search to verify each facility
   - Check: Does it exist? Does location match? Is it legitimate?
3. If NO or names are UNCLEAR:
   - Skip verification entirely
   - Keep your original decision based on other factors
4. Update your decision ONLY if verification reveals important findings

Check for red flags:
- Facility doesn't exist in Google (if you searched)
- Address/location mismatch (if you searched)
- Suspicious or fake facilities (if you searched)

IMPORTANT: 
- Search format: "[Exact Facility Name from Document] + [Location]"
- Only search if you have a clear, specific facility name
- Absence of facility name does NOT mean fraud

Provide your FINAL decision in JSON format.
If you performed searches, include a "clinic_verification" field with results.
If you did NOT perform searches (no clear facility name), note this in your explanation.
"""
            
            try:
                # Text-only request with Google Search
                final_response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=verification_prompt,
                    config=types.GenerateContentConfig(
                        **config,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                
                if final_response.text:
                    final_response_text = final_response.text
                    print(f"    ✓ Clinic verification complete")
                    
                    # Extract grounding metadata from verification response
                    if hasattr(final_response, 'candidates') and final_response.candidates:
                        for candidate in final_response.candidates:
                            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                                gm = candidate.grounding_metadata
                                metadata_entry = {
                                    "search_performed": True,
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                # Extract search queries from search_entry_point
                                search_queries = []
                                if hasattr(gm, 'search_entry_point') and gm.search_entry_point:
                                    # The search_entry_point contains information about searches performed
                                    search_entry_str = str(gm.search_entry_point)
                                    metadata_entry["search_entry_point"] = search_entry_str
                                    
                                    # Try to parse queries if available
                                    if hasattr(gm.search_entry_point, 'rendered_content'):
                                        metadata_entry["search_queries_html"] = gm.search_entry_point.rendered_content
                                
                                # Extract grounding chunks (search results with URLs and titles)
                                search_results = []
                                supports = []  # Initialize here to avoid reference errors
                                if hasattr(gm, 'grounding_chunks') and gm.grounding_chunks:
                                    for idx, chunk in enumerate(gm.grounding_chunks):
                                        result_info = {
                                            "index": idx,
                                            "source": "web"
                                        }
                                        if hasattr(chunk, 'web') and chunk.web:
                                            if hasattr(chunk.web, 'uri'):
                                                result_info["url"] = chunk.web.uri
                                            if hasattr(chunk.web, 'title'):
                                                result_info["title"] = chunk.web.title
                                        if "url" in result_info or "title" in result_info:
                                            search_results.append(result_info)
                                    
                                    metadata_entry["search_results"] = search_results
                                    metadata_entry["total_results"] = len(search_results)
                                    print(f"    📚 Found {len(search_results)} search result(s)")
                                
                                # Extract grounding supports (which parts of the response used which sources)
                                if hasattr(gm, 'grounding_supports') and gm.grounding_supports:
                                    supports = []
                                    for support in gm.grounding_supports:
                                        support_info = {}
                                        # Extract the text segment that was supported
                                        if hasattr(support, 'segment') and support.segment:
                                            if hasattr(support.segment, 'text'):
                                                support_info["verified_text"] = support.segment.text
                                            if hasattr(support.segment, 'start_index'):
                                                support_info["start_index"] = support.segment.start_index
                                            if hasattr(support.segment, 'end_index'):
                                                support_info["end_index"] = support.segment.end_index
                                        # Extract which search results supported this claim
                                        if hasattr(support, 'grounding_chunk_indices'):
                                            indices = list(support.grounding_chunk_indices)
                                            support_info["source_indices"] = indices
                                            # Map to actual URLs for reference
                                            if search_results:
                                                support_info["sources"] = [
                                                    search_results[i] for i in indices 
                                                    if i < len(search_results)
                                                ]
                                        if support_info:
                                            supports.append(support_info)
                                    
                                    metadata_entry["grounding_supports"] = supports
                                    metadata_entry["verified_statements"] = len(supports)
                                    print(f"    ✓ Verified {len(supports)} statement(s) with search results")
                                
                                # Extract retrieval metadata if available
                                if hasattr(gm, 'retrieval_metadata') and gm.retrieval_metadata:
                                    metadata_entry["retrieval_metadata"] = str(gm.retrieval_metadata)
                                
                                # Add to grounding_metadata list
                                if search_results or supports:
                                    grounding_metadata.append(metadata_entry)
                                    
                                    # Also create a summary for easier display
                                    summary = {
                                        "total_searches": 1,
                                        "total_results": len(search_results),
                                        "verified_statements": len(supports) if supports else 0,
                                        "top_sources": [
                                            r.get("title", r.get("url", "Unknown")) 
                                            for r in search_results[:5]
                                        ]
                                    }
                                    metadata_entry["summary"] = summary
                else:
                    print(f"    ⚠️ No verification response, using initial analysis")
                    
            except Exception as e:
                print(f"    ⚠️ Clinic verification error: {str(e)}")
                print(f"    → Using initial analysis without verification")
        
        # Parse response
        try:
            response_text = final_response_text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            decision = json.loads(response_text.strip())
            
            # Add grounding metadata to decision for transparency
            if grounding_metadata:
                decision["google_search_grounding"] = grounding_metadata
                print(f"  ✓ Google Search was used - {len(grounding_metadata)} grounding metadata entries")
            
            # Add clinic verification flag
            if self.enable_clinic_verification:
                decision["clinic_verification_enabled"] = True
        except Exception as e:
            decision = {
                "decision": "UNCERTAIN",
                "explanation": f"Error parsing LLM response: {str(e)}",
                "raw_response": final_response_text
            }
            if grounding_metadata:
                decision["google_search_grounding"] = grounding_metadata
        
        # Compile final result
        result = {
            "claim_number": claim_number,
            "timestamp": datetime.now().isoformat(),
            "claim_data": {
                "description": claim_data["description"],
                "documents": claim_data["documents"]
            },
            "image_metadata": image_metadata,
            "llm_decision": decision,
            "expected_answer": claim_data.get("expected_answer"),
            "matches_expected": self._compare_decisions(
                decision.get("decision"),
                claim_data.get("expected_answer")
            ) if claim_data.get("expected_answer") else None
        }
        
        return result
    
    def _build_analysis_prompt(self, claim_data: Dict, image_metadata: List[Dict]) -> str:
        """Build the analysis prompt for the LLM."""
        prompt_parts = [self.system_prompt]
        
        prompt_parts.append("\n\n## CLAIM TO ANALYZE\n")
        
        # Add claim description
        prompt_parts.append(f"### Claim Description\n{claim_data['description']}\n")
        
        # Add supporting documents
        if claim_data["documents"]:
            prompt_parts.append("\n### Supporting Documents (Text)\n")
            for doc in claim_data["documents"]:
                prompt_parts.append(f"\n**{doc['filename']}**\n```\n{doc['content']}\n```\n")
        
        # Add image metadata
        if image_metadata:
            prompt_parts.append("\n### Supporting Documents (Images - Extracted Metadata)\n")
            for img_meta in image_metadata:
                prompt_parts.append(f"\n**{img_meta['filename']}**\n```json\n{json.dumps(img_meta['metadata'], indent=2)}\n```\n")
        
        prompt_parts.append("\n### Images Attached\n")
        prompt_parts.append(f"{len(image_metadata)} image(s) are attached for your direct visual analysis.\n")
        
        # Add Google Search availability notice if enabled
        if self.enable_clinic_verification:
            prompt_parts.append("\n### 🔍 Google Search Grounding Enabled\n")
            prompt_parts.append("You have access to Google Search to verify medical facilities, hospitals, and clinics.")
            prompt_parts.append("Simply mention or ask about any medical facility, and relevant search results will be provided.")
            prompt_parts.append("Use this to verify the authenticity of medical certificates and documents.\n")
        
        prompt_parts.append("\n## YOUR TASK\n")
        prompt_parts.append("Analyze all provided information and make a decision: APPROVE, DENY, or UNCERTAIN.")
        prompt_parts.append("Follow the decision guidelines strictly and check for all fraud indicators.")
        if self.enable_clinic_verification:
            prompt_parts.append("Use Google Search to verify any medical facilities mentioned in certificates if needed.")
        prompt_parts.append("Return your response in the required JSON format.")
        
        return "\n".join(prompt_parts)
    
    def _compare_decisions(self, llm_decision: str, expected_answer: Dict) -> Dict:
        """Compare LLM decision with expected answer."""
        if not expected_answer:
            return None
        
        expected_decision = expected_answer.get("decision")
        acceptable = expected_answer.get("acceptable_decision")
        
        matches = llm_decision == expected_decision
        matches_acceptable = acceptable and llm_decision == acceptable
        
        return {
            "exact_match": matches,
            "acceptable_match": matches_acceptable,
            "expected": expected_decision,
            "acceptable_alternative": acceptable,
            "actual": llm_decision
        }
    
    async def process_multiple_claims(self, claim_numbers: List[int]) -> Dict:
        """Process multiple claims and save results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        num_claims = len(claim_numbers)
        
        # Create results directory for this run
        run_dir = self.results_dir / f"run_{timestamp}_{num_claims}_claims"
        run_dir.mkdir(exist_ok=True)
        
        results = []
        stats = {
            "total_claims": num_claims,
            "approved": 0,
            "denied": 0,
            "uncertain": 0,
            "exact_matches": 0,
            "acceptable_matches": 0,
            "mismatches": 0
        }
        
        for claim_num in claim_numbers:
            try:
                print(f"\n🔄 Processing claim {claim_num}...")
                result = await self.process_claim(claim_num)
                results.append(result)
                
                # Update stats - map decision to correct key
                decision = result["llm_decision"].get("decision", "UNCERTAIN").upper()
                if decision == "APPROVE":
                    stats["approved"] += 1
                elif decision == "DENY":
                    stats["denied"] += 1
                elif decision == "UNCERTAIN":
                    stats["uncertain"] += 1
                
                if result.get("matches_expected"):
                    if result["matches_expected"]["exact_match"]:
                        stats["exact_matches"] += 1
                    elif result["matches_expected"]["acceptable_match"]:
                        stats["acceptable_matches"] += 1
                    else:
                        stats["mismatches"] += 1
                
                # Save individual claim result
                claim_file = run_dir / f"claim_{claim_num}.json"
                with open(claim_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                # Add 30 second delay between claims to avoid API rate limits
                # Skip delay for the last claim
                if claim_num != claim_numbers[-1]:
                    print(f"⏱️  Waiting 30 seconds before next claim to avoid API rate limits...")
                    await asyncio.sleep(30)
                    
            except Exception as e:
                print(f"❌ Error processing claim {claim_num}: {str(e)}")
                results.append({
                    "claim_number": claim_num,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Still add delay even on error
                if claim_num != claim_numbers[-1]:
                    print(f"⏱️  Waiting 30 seconds before next claim...")
                    await asyncio.sleep(30)
        
        # Calculate accuracy
        if stats["exact_matches"] + stats["acceptable_matches"] + stats["mismatches"] > 0:
            stats["accuracy"] = (stats["exact_matches"] + stats["acceptable_matches"]) / (
                stats["exact_matches"] + stats["acceptable_matches"] + stats["mismatches"]
            )
        else:
            stats["accuracy"] = 0.0
        
        # Save summary
        summary = {
            "run_timestamp": timestamp,
            "claims_processed": claim_numbers,
            "statistics": stats,
            "results": results
        }
        
        summary_file = run_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✓ Results saved to: {run_dir}")
        print(f"✓ Processed {num_claims} claims")
        print(f"✓ Accuracy: {stats['accuracy']*100:.1f}%")
        
        return summary
