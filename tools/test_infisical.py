import os
import sys

# Ensure the root directory is in the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.clients.infisical_client import InfisicalManager

def test():
    infisical = InfisicalManager()
    if not infisical.is_connected:
        print("❌ Infisical not connected.")
        return

    print(f"Connected to Infisical. Project ID: {infisical.project_id}")
    print(f"Default Env: {infisical.default_env}")

    try:
        all_secrets = infisical.list_secrets()
        print(f"\nFound {len(all_secrets)} secrets in {infisical.default_env} environment:")
        for s in all_secrets:
            # Using the extraction logic we have in the client
            key_name = getattr(s, 'secret_key', None) or getattr(s, 'secretKey', None) or (s.get('secret_key', None) if isinstance(s, dict) else None)
            
            # If still None, try to inspect the object
            if not key_name:
                if hasattr(s, 'secret'):
                    nested = getattr(s, 'secret')
                    key_name = getattr(nested, 'secret_key', None) or getattr(nested, 'secretKey', None)
            
            print(f" - {key_name}")

        keys = infisical.get_marketaux_keys()
        print(f"\nMarketAux keys found: {len(keys)}")
        for k in keys:
            print(f" - {k[:4]}...{k[-4:] if len(k) > 8 else ''}")

    except Exception as e:
        print(f"❌ Error listing secrets: {e}")

if __name__ == "__main__":
    test()
