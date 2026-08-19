import httpx
import getpass
import sys

BASE_URL = "https://getyourjob-e9dn.onrender.com"

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def main():
    print("=" * 60)
    print("            AutoMail API Diagnostic Sender")
    print("=" * 60)
    print("This script will help diagnose sending issues on the Render backend.")
    print("Choose authentication method:")
    print(" 1) Log in with Email & Password")
    print(" 2) Paste JWT Token directly (copied from browser console 'getnewjob_token')")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    token = None
    
    if choice == "1":
        email = input("Email [default: adityacodes404@gmail.com]: ").strip()
        if not email:
            email = "adityacodes404@gmail.com"
        if "@" not in email:
            email += "@gmail.com"
            
        password = getpass.getpass("Password: ")
        
        print(f"\nAttempting to log in to {BASE_URL}...")
        try:
            resp = httpx.post(f"{BASE_URL}/auth/login", json={
                "email": email,
                "password": password
            }, timeout=15.0)
            if resp.status_code != 200:
                print(f"[ERROR] Login failed ({resp.status_code}): {resp.text}")
                sys.exit(1)
            token = resp.json()["access_token"]
            print("[SUCCESS] Logged in successfully!")
        except Exception as e:
            print(f"[ERROR] Could not connect to backend: {e}")
            sys.exit(1)
            
    elif choice == "2":
        token = input("Paste JWT Token: ").strip()
        if not token:
            print("[ERROR] Token cannot be empty.")
            sys.exit(1)
    else:
        print("[ERROR] Invalid choice.")
        sys.exit(1)
        
    headers = get_headers(token)
    
    # 1. Fetch settings to see what is currently configured
    print("\n1. Fetching current user settings...")
    try:
        settings_resp = httpx.get(f"{BASE_URL}/settings", headers=headers, timeout=15.0)
        if settings_resp.status_code == 200:
            st = settings_resp.json()
            print("Settings currently configured on server:")
            print(f" - SMTP Host: {st.get('smtp_host')}")
            print(f" - SMTP Port: {st.get('smtp_port')}")
            print(f" - SMTP User: {st.get('smtp_user')}")
            print(f" - Has SMTP Password Saved: {st.get('has_smtp_password')}")
            print(f" - Has Google OAuth Connected: {st.get('has_google_oauth')}")
            print(f" - Send Mode: {st.get('send_mode')}")
        else:
            print(f"[ERROR] Failed to fetch settings ({settings_resp.status_code}): {settings_resp.text}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)
        
    # 2. Create target contact
    recipient_email = input("\nEnter recipient email [default: adityaanurag461@gmail.com]: ").strip()
    if not recipient_email:
        recipient_email = "adityaanurag461@gmail.com"
        
    print(f"\n2. Creating test contact for {recipient_email}...")
    contact_payload = {
        "name": "Aditya Anurag",
        "company": "Test Diagnostics Org",
        "role": "Software Engineer",
        "email": recipient_email,
        "source": "manual"
    }
    
    contact_id = None
    try:
        contact_resp = httpx.post(f"{BASE_URL}/contacts", headers=headers, json=contact_payload, timeout=15.0)
        if contact_resp.status_code == 201:
            contact_data = contact_resp.json()
            contact_id = contact_data["id"]
            print(f"[SUCCESS] Contact created with ID: {contact_id}")
        else:
            print(f"[ERROR] Failed to create contact ({contact_resp.status_code}): {contact_resp.text}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)
        
    # 3. Personalize email template
    print(f"\n3. Personalizing email for contact ID {contact_id}...")
    try:
        pers_resp = httpx.post(f"{BASE_URL}/queue/{contact_id}/personalize", headers=headers, timeout=15.0)
        if pers_resp.status_code == 200:
            pers_data = pers_resp.json()
            print("[SUCCESS] Email personalized!")
            print(f" - Subject: {pers_data.get('subject')}")
            print(f" - Body Preview (first 100 chars): {pers_data.get('body')[:100]}...")
        else:
            print(f"[ERROR] Personalization failed ({pers_resp.status_code}): {pers_resp.text}")
            # Try to continue if subject/body are already set
            
    except Exception as e:
        print(f"[ERROR] Connection failed during personalization: {e}")
        sys.exit(1)
        
    # 4. Dispatch email immediately
    print(f"\n4. Triggering immediate dispatch (Send Now) for contact ID {contact_id}...")
    try:
        dispatch_resp = httpx.post(f"{BASE_URL}/queue/{contact_id}/dispatch", headers=headers, timeout=15.0)
        if dispatch_resp.status_code == 200:
            print("\n" + "=" * 60)
            print("🎉 SUCCESS! Email sent successfully!")
            print("=" * 60)
            print(f"Response: {dispatch_resp.json()}")
        else:
            print("\n" + "=" * 60)
            print(f"❌ ERROR! Dispatch failed with status {dispatch_resp.status_code}")
            print("=" * 60)
            print(f"Server response body: {dispatch_resp.text}")
            print("\nDiagnostics suggestion:")
            if "SMTP authentication failed" in dispatch_resp.text:
                print(" -> Check your SMTP App Password in Settings. Ensure 2-Factor Auth is enabled on your Gmail account and you are using a generated 'App Password', NOT your primary login password.")
            elif "XOAUTH2 authentication failed" in dispatch_resp.text:
                print(" -> Stale Google OAuth credentials detected. Save a new SMTP password in the Settings page to clear Google OAuth tokens and force standard password-based sending.")
            elif "SMTP not configured" in dispatch_resp.text:
                print(" -> Go to the Settings page and enter your SMTP Host (smtp.gmail.com), Port (587), Username, and App Password, then click Save.")
    except Exception as e:
        print(f"[ERROR] Connection failed during dispatch: {e}")

if __name__ == "__main__":
    main()
