"""
Google Search Tool for verifying medical clinics and hospitals.
Uses Google Custom Search API to verify clinic/hospital existence and legitimacy.
"""

import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class GoogleSearchTool:
    """Tool for searching Google to verify medical facilities."""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.enabled = bool(self.api_key and self.search_engine_id)
        
        if not self.enabled:
            print("⚠️  Google Search API not configured. Clinic verification will be disabled.")
            print("   To enable: Add GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID to .env")
    
    def search(self, query: str, num_results: int = 5) -> Dict:
        """
        Perform a Google search and return results.
        
        Args:
            query: Search query string
            num_results: Number of results to return (1-10)
            
        Returns:
            Dict with search results and metadata
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Google Search API not configured",
                "results": []
            }
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": min(num_results, 10)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant information
            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "displayLink": item.get("displayLink")
                })
            
            return {
                "success": True,
                "query": query,
                "total_results": data.get("searchInformation", {}).get("totalResults", "0"),
                "results": results
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Search request timed out",
                "results": []
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Search request failed: {str(e)}",
                "results": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "results": []
            }
    
    def verify_medical_facility(self, facility_name: str, location: Optional[str] = None) -> Dict:
        """
        Verify if a medical facility exists and is legitimate.
        
        Args:
            facility_name: Name of the clinic/hospital
            location: Optional location/city to narrow search
            
        Returns:
            Dict with verification results
        """
        if not self.enabled:
            return {
                "verified": None,
                "confidence": 0.0,
                "message": "Google Search API not configured",
                "search_results": []
            }
        
        # Build search query
        query_parts = [facility_name]
        if location:
            query_parts.append(location)
        query_parts.extend(["hospital", "OR", "clinic", "OR", "medical"])
        
        query = " ".join(query_parts)
        
        # Perform search
        search_result = self.search(query, num_results=5)
        
        if not search_result["success"]:
            return {
                "verified": None,
                "confidence": 0.0,
                "message": f"Search failed: {search_result.get('error')}",
                "search_results": []
            }
        
        results = search_result["results"]
        
        # Analyze results
        if not results:
            return {
                "verified": False,
                "confidence": 0.8,
                "message": f"No results found for '{facility_name}'. Facility may not exist or name may be incorrect.",
                "search_results": []
            }
        
        # Check if facility name appears in results
        facility_lower = facility_name.lower()
        relevant_results = []
        exact_match = False
        partial_match = False
        
        for result in results:
            title_lower = result["title"].lower()
            snippet_lower = result["snippet"].lower()
            
            # Check for matches
            if facility_lower in title_lower or facility_lower in snippet_lower:
                relevant_results.append(result)
                
                # Check for exact match
                if facility_lower in title_lower:
                    exact_match = True
                else:
                    partial_match = True
        
        # Determine verification status
        if exact_match:
            return {
                "verified": True,
                "confidence": 0.9,
                "message": f"Facility '{facility_name}' found in search results with strong match.",
                "search_results": relevant_results[:3]  # Top 3 relevant results
            }
        elif partial_match or len(relevant_results) > 0:
            return {
                "verified": True,
                "confidence": 0.7,
                "message": f"Facility '{facility_name}' found with partial match. May need verification.",
                "search_results": relevant_results[:3]
            }
        else:
            return {
                "verified": False,
                "confidence": 0.6,
                "message": f"No clear match found for '{facility_name}'. Facility may not exist or search terms may be incorrect.",
                "search_results": results[:3]  # Show what was found
            }
    
    def get_tool_description(self) -> Dict:
        """
        Return tool description for LLM function calling.
        """
        return {
            "type": "function",
            "function": {
                "name": "verify_medical_facility",
                "description": "Search Google to verify if a medical clinic or hospital exists and is legitimate. Use this when you find a medical facility name in claim documents and want to verify its authenticity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "facility_name": {
                            "type": "string",
                            "description": "The name of the medical clinic, hospital, or healthcare facility to verify"
                        },
                        "location": {
                            "type": "string",
                            "description": "Optional location, city, or address to narrow the search"
                        }
                    },
                    "required": ["facility_name"]
                }
            }
        }
    
    def execute_tool_call(self, tool_call: Dict) -> Dict:
        """
        Execute a tool call from the LLM.
        
        Args:
            tool_call: Tool call object from LLM
            
        Returns:
            Tool call result
        """
        function_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})
        
        if function_name == "verify_medical_facility":
            facility_name = arguments.get("facility_name")
            location = arguments.get("location")
            
            if not facility_name:
                return {
                    "error": "Missing required parameter: facility_name"
                }
            
            return self.verify_medical_facility(facility_name, location)
        else:
            return {
                "error": f"Unknown function: {function_name}"
            }


# Test function
def test_search_tool():
    """Test the Google Search Tool."""
    tool = GoogleSearchTool()
    
    if not tool.enabled:
        print("❌ Google Search API not configured")
        print("\nTo set up:")
        print("1. Go to https://developers.google.com/custom-search/v1/overview")
        print("2. Create a Custom Search Engine")
        print("3. Get your API key and Search Engine ID")
        print("4. Add to .env file:")
        print("   GOOGLE_SEARCH_API_KEY=your_key_here")
        print("   GOOGLE_SEARCH_ENGINE_ID=your_engine_id_here")
        return
    
    print("✓ Google Search Tool initialized")
    print("\nTesting facility verification...")
    
    # Test with a real hospital
    result = tool.verify_medical_facility("Mayo Clinic", "Rochester Minnesota")
    print(f"\nTest 1 - Mayo Clinic:")
    print(f"  Verified: {result['verified']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Message: {result['message']}")
    
    # Test with a fake hospital
    result = tool.verify_medical_facility("XYZ Fake Hospital 12345", "Nowhere City")
    print(f"\nTest 2 - Fake Hospital:")
    print(f"  Verified: {result['verified']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Message: {result['message']}")


if __name__ == "__main__":
    test_search_tool()
