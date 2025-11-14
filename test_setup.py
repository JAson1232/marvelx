#!/usr/bin/env python3
"""
Quick test script to verify the claim processing system setup.
"""

import os
import sys
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has API key."""
    print("Checking .env file...")
    if not Path(".env").exists():
        print("  ❌ .env file not found")
        print("  💡 Run: cp .env.example .env")
        return False
    
    with open(".env", "r") as f:
        content = f.read()
        if "your_google_gemini_api_key_here" in content or not "GOOGLE_API_KEY=" in content:
            print("  ⚠️  GOOGLE_API_KEY not set in .env")
            return False
    
    print("  ✓ .env file configured")
    return True

def check_dependencies():
    """Check if required Python packages are installed."""
    print("\nChecking Python dependencies...")
    required = [
        "fastapi",
        "uvicorn",
        "google.genai",
        "dotenv",
        "PIL",
        "pytesseract",
        "toml"
    ]
    
    missing = []
    for package in required:
        try:
            if package == "dotenv":
                __import__("dotenv")
            elif package == "PIL":
                __import__("PIL")
            elif package == "toml":
                __import__("toml")
            else:
                __import__(package.replace("-", "_"))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n  💡 Install missing packages: pip install {' '.join(missing)}")
        return False
    
    return True

def check_tesseract():
    """Check if Tesseract OCR is installed."""
    print("\nChecking Tesseract OCR...")
    import subprocess
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"  ✓ {version}")
            return True
    except FileNotFoundError:
        pass
    
    print("  ⚠️  Tesseract not found (OCR will not work)")
    print("  💡 Install: brew install tesseract tesseract-lang")
    return False

def check_claim_data():
    """Check if claim data directories exist."""
    print("\nChecking claim data...")
    base_dir = Path(".")
    found = 0
    for i in range(1, 26):
        claim_dir = base_dir / f"claim {i}"
        if claim_dir.exists():
            found += 1
    
    if found == 25:
        print(f"  ✓ All 25 claim directories found")
        return True
    else:
        print(f"  ⚠️  Only {found}/25 claim directories found")
        return False

def check_files():
    """Check if required files exist."""
    print("\nChecking required files...")
    required_files = [
        "main.py",
        "claim_processor.py",
        "system_prompt.toml",
        "requirements.txt",
        "templates/index.html",
        "static/style.css",
        "static/script.js"
    ]
    
    all_found = True
    for file in required_files:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ❌ {file}")
            all_found = False
    
    return all_found

def test_api_connection():
    """Test if we can connect to Google Gemini API."""
    print("\nTesting API connection...")
    try:
        from dotenv import load_dotenv
        from google import genai
        
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key or api_key == "your_google_gemini_api_key_here":
            print("  ⚠️  API key not configured")
            return False
        
        # Set API key and create client
        os.environ["GOOGLE_API_KEY"] = api_key
        client = genai.Client()
        
        # Try a simple generation as a test
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say hello"
        )
        
        if response.text:
            print("  ✓ Successfully connected to Google Gemini API")
            return True
        else:
            print("  ❌ API returned empty response")
            return False
        
    except Exception as e:
        print(f"  ❌ API connection failed: {str(e)}")
        return False

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  Insurance Claim Processing System - Setup Verification   ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    results = []
    
    results.append(("Environment File", check_env_file()))
    results.append(("Python Dependencies", check_dependencies()))
    results.append(("Tesseract OCR", check_tesseract()))
    results.append(("Claim Data", check_claim_data()))
    results.append(("Required Files", check_files()))
    
    # Only test API if env is configured
    if results[0][1]:
        results.append(("API Connection", test_api_connection()))
    
    print("\n" + "="*64)
    print("SUMMARY")
    print("="*64)
    
    for check, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{check:.<40} {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("="*64)
    
    if all_passed:
        print("\n✓ All checks passed! You're ready to run the application.")
        print("\n🚀 Start the application:")
        print("   ./run.sh")
        print("   or")
        print("   python main.py")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
