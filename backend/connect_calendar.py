import os
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

api_key = os.getenv("COMPOSIO_API_KEY")
print(f"Using API key: {api_key[:8]}...")

client = Composio(api_key=api_key)

# Step 1: Find the Google Calendar auth config ID
print("\n1. Finding Google Calendar auth config...")
try:
    configs = client.auth_configs.list(toolkit_slug="googlecalendar")
    items = configs.items if hasattr(configs, 'items') else list(configs)
    if items:
        auth_config = items[0]
        auth_config_id = auth_config.id if hasattr(auth_config, 'id') else str(auth_config)
        print(f"   Found auth config: {auth_config_id}")
    else:
        print("   No auth config found! Please create one in the Composio dashboard first.")
        exit(1)
except Exception as e:
    print(f"   Error: {e}")
    # Fallback: use the ID visible in the dashboard screenshot
    auth_config_id = "ac_MfsrDjB-dLVd"
    print(f"   Using fallback auth_config_id: {auth_config_id}")

# Step 2: Initiate the connection
print(f"\n2. Initiating Google Calendar connection with auth_config_id={auth_config_id}...")
try:
    result = client.connected_accounts.initiate(
        user_id="default",
        auth_config_id=auth_config_id,
    )
    # Try various attribute names for the redirect URL
    redirect_url = None
    for attr in ['redirect_url', 'redirectUrl', 'url']:
        if hasattr(result, attr):
            redirect_url = getattr(result, attr)
            break
    
    if not redirect_url:
        # Try dict-style access
        try:
            redirect_url = result['redirect_url'] or result['redirectUrl']
        except:
            redirect_url = str(result)
    
    print("\n========================================================")
    print("ACTION REQUIRED:")
    print("Open this link in your browser to connect Google Calendar:")
    print(redirect_url)
    print("========================================================\n")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
