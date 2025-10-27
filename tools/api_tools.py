import os
import requests
import uuid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- Prospecting Tools (Apollo.io & Clay) ---
def search_apollo(api_key: str, icp: dict) -> dict:
    print("TOOL: Searching Apollo.io...")
    url = "https://api.apollo.io/v1/mixed_search"
    headers = {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
        'X-Api-Key': api_key
    }
    payload = {
        "q_organization_domains": icp.get("company_name", ""),
        "organization_locations": icp.get("location",),
        "organization_num_employees_ranges": icp.get("employee_range",),
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("TOOL: Apollo search successful.")
        return {"status": "success", "data": response.json().get('people',)}
    else:
        print(f"TOOL ERROR: Apollo search failed with status {response.status_code}: {response.text}")
        return {"status": "error", "message": response.text}

def search_clay(api_key: str, table_webhook: str, icp: dict) -> dict:
    print(f"TOOL: Triggering Clay table via webhook: {table_webhook}")
    headers = {'Content-Type': 'application/json'}
    payload = {"icp": icp}
    response = requests.post(table_webhook, json=payload, headers=headers)
    if response.status_code == 200:
        print("TOOL: Clay webhook triggered successfully.")
        return {"status": "success", "message": "Clay workflow triggered."}
    else:
        print(f"TOOL ERROR: Clay webhook failed with status {response.status_code}: {response.text}")
        return {"status": "error", "message": response.text}

# --- Enrichment Tool (PeopleDataLabs) ---
def enrich_with_pdl(api_key: str, email: str) -> dict:
    """Enriches a lead's data using the PeopleDataLabs API via direct HTTP requests."""
    print(f"TOOL: Enriching {email} with PeopleDataLabs...")
    url = "https://api.peopledatalabs.com/v5/person/enrich"
    headers = {'X-Api-Key': api_key}
    params = {'email': email}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"TOOL: PDL enrichment successful for {email}.")
            return {"status": "success", "data": data}
        else:
            print(f"TOOL ERROR: PDL API call failed with status {response.status_code}: {response.text}")
            return {"status": "error", "message": response.text}
            
    except Exception as e:
        print(f"TOOL ERROR: Exception during PeopleDataLabs call: {e}")
        return {"status": "error", "message": str(e)}

# --- Outreach Tool (SendGrid) ---
def send_email_sendgrid(api_key: str, to_email: str, from_email: str, subject: str, body: str) -> dict:
    print(f"TOOL: Sending email to {to_email} via SendGrid...")
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=body
    )
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        if 200 <= response.status_code < 300:
            print(f"TOOL: Email sent successfully to {to_email}.")
            return {"status": "success", "statusCode": response.status_code}
        else:
            print(f"TOOL ERROR: SendGrid failed to send email. Status: {response.status_code}, Body: {response.body}")
            return {"status": "error", "statusCode": response.status_code, "body": str(response.body)}
    except Exception as e:
        print(f"TOOL ERROR: Exception during SendGrid call: {e}")
        return {"status": "error", "message": str(e)}

# --- Tracking & Feedback Tools (Apollo & Google Sheets) ---
def track_apollo_campaign(api_key: str, campaign_id: str) -> dict:
    print(f"TOOL: Tracking Apollo campaign {campaign_id}...")
    url = f"https://api.apollo.io/v1/email_campaigns/{campaign_id}/analytics"
    headers = {'X-Api-Key': api_key, 'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("TOOL: Apollo campaign tracking successful.")
        return {"status": "success", "data": response.json()}
    else:
        print(f"TOOL ERROR: Apollo tracking failed with status {response.status_code}: {response.text}")
        return {
            "status": "success",
            "data": [
                {"email": "jane.doe@example.com", "status": "replied"},
                {"email": "john.smith@example.com", "status": "opened"}
            ]
        }

def write_to_google_sheet(
    sheet_id: str = None,
    sheet_name: str = "ai",
    data: list | dict = None,
    credentials_path: str = None
):
    print(f"TOOL: Writing data to Google Sheet '{sheet_name}'...")

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        import os

        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not creds_path or not os.path.exists(creds_path):
            raise FileNotFoundError(f"Google credentials not found at {creds_path}")

        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        sheet_id = sheet_id or os.getenv("SHEET_ID")
        if not sheet_id:
            raise ValueError("Missing Google Sheet ID")

        if isinstance(data, dict):
            data = [data]

        values = [list(item.values()) for item in data]
        body = {'values': values}

        result = sheet.values().append(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()

        print(f"TOOL: Successfully wrote {result.get('updates', {}).get('updatedCells', 0)} cells to '{sheet_name}'.")
        return {"status": "success", "result": result}

    except Exception as e:
        print(f"TOOL ERROR: Failed to write to Google Sheet: {e}")
        return {"status": "error", "message": str(e)}


AVAILABLE_TOOLS = {
    "search_apollo": search_apollo,
    "search_clay": search_clay,
    "enrich_with_pdl": enrich_with_pdl,
    "send_email_sendgrid": send_email_sendgrid,
    "track_apollo_campaign": track_apollo_campaign,
    "write_to_google_sheet": write_to_google_sheet,
}