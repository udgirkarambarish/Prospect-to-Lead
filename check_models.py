import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

print("--- Step 1: Basic Network Connectivity Test ---")
try:
    # Test connection to a general Google endpoint with a 15-second timeout
    response = requests.get("https://www.googleapis.com/discovery/v1/apis", timeout=15)
    if response.status_code == 200:
        print("Successfully connected to Google's API discovery service. Network connection is OK.")
    else:
        print(f"Failed to connect to Google's API discovery service. Status code: {response.status_code}")
        print("This may indicate a network issue or firewall.")
        exit()
except requests.exceptions.RequestException as e:
    print(f"A network error occurred during the basic connectivity test: {e}")
    print("This strongly suggests a local network issue (firewall, proxy, VPN, or internet connection).")
    exit()

print("\n--- Step 2: Checking for available Gemini models ---")

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in.env file.")
    exit()

try:
    # Configure the API key
    genai.configure(api_key=api_key)

    print("\nModels you can use for 'generateContent':")
    model_found = False
    # List all models and filter for the ones that can generate content
    for m in genai.list_models():
      if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")
        model_found = True
    
    if not model_found:
        print("No models supporting 'generateContent' were found.")
        print("This means the 'Generative Language API' is likely not enabled or billing is not active on your project.")
            
except Exception as e:
    print(f"\nAn error occurred while communicating with the Gemini API: {e}")
    print("\nTroubleshooting steps:")
    print("1. Verify your GOOGLE_API_KEY in the.env file is correct.")
    print("2. Ensure the 'Generative Language API' is enabled in your Google Cloud project.")
    print("3. CRITICAL: Make sure your Google Cloud project has an active billing account linked.")
    print("4. If you are on a corporate network, a firewall or VPN might be blocking the connection.")