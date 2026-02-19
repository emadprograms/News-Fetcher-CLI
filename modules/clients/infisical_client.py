from infisical_client import InfisicalClient, ClientSettings, GetSecretOptions, AuthenticationOptions, UniversalAuthMethod
import os
import toml

class InfisicalManager:
    def __init__(self, project_id=None):
        """
        Initializes the Infisical Client using Universal Auth (Client ID & Secret).
        Priority: 
        1. Environment Vars (INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET)
        2. Local Secrets (secrets.toml -> [infiscal] section)
        """
        self.client = None
        self.is_connected = False
        self.project_id = project_id 
        
        # 1. Try Env Vars
        client_id = os.getenv("INFISICAL_CLIENT_ID")
        client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
        if not self.project_id:
            self.project_id = os.getenv("INFISICAL_PROJECT_ID")
        
        # 2. Key Fallback: Check secrets.toml if env vars missing
        # We also check for project_id here if it's still missing
        if not client_id or not client_secret or not self.project_id:
            try:
                data = toml.load(".streamlit/secrets.toml")
                sec = data.get("infisical")
                if sec:
                    if not client_id: client_id = sec.get("client_id")
                    if not client_secret: client_secret = sec.get("client_secret")
                    if not self.project_id: self.project_id = sec.get("project_id")
            except:
                pass

        if client_id and client_secret:
            try:
                auth_method = UniversalAuthMethod(client_id=client_id, client_secret=client_secret)
                options = AuthenticationOptions(universal_auth=auth_method)
                self.client = InfisicalClient(ClientSettings(auth=options))
                self.is_connected = True
                print("✅ Infisical Client Connected.")
            except Exception as e:
                print(f"❌ Infisical Connection Failed: {e}")
        else:
            print("⚠️ Infisical Credentials not found in ENV or secrets.toml.")

    def get_secret(self, secret_name, environment="dev", path="/"):
        """
        Retrieves a single secret value.
        """
        if not self.is_connected:
            return None
        
        try:
            # SDK v2: Use snake_case arguments
            secret = self.client.getSecret(options=GetSecretOptions(
                secret_name=secret_name,
                project_id=self.project_id, 
                environment=environment,
                path=path
            ))
            return secret.secret_value
        except Exception as e:
            # Try lowercase fallback
            if secret_name.isupper() or "_" in secret_name:
                try:
                    secret = self.client.getSecret(options=GetSecretOptions(
                        secret_name=secret_name.lower(),
                        project_id=self.project_id, 
                        environment=environment,
                        path=path
                    ))
                    return secret.secret_value
                except:
                    pass
            print(f"❌ Failed to fetch secret '{secret_name}': {e}")
            return None

    def get_marketaux_keys(self):
        """
        Helper to fetch keys. Supports 2 formats:
        1. Single Secret (Legacy): MARKETAUX_API_KEYS (comma-separated or JSON)
        2. Individual Secrets (New): marketaux_news_data_API_KEY_1, _2, etc.
        """
        keys = []
        
        # 1. Try Legacy List
        val = self.get_secret("MARKETAUX_API_KEYS")
        if val:
            if "[" in val and "]" in val:
                 import json
                 try:
                     keys.extend(json.loads(val))
                 except:
                     pass
            elif "," in val:
                keys.extend([k.strip() for k in val.split(",") if k.strip()])
            else:
                keys.append(val)
        
        # 2. Try Individual Secrets (1..5)
        # We loop until we fail to find one, or hit a reasonable limit (e.g. 10)
        # The user specifically asked for "1 and then 2 and 3"
        for i in range(1, 11):
            name = f"marketaux_news_data_API_KEY_{i}"
            val = self.get_secret(name)
            if val:
                keys.append(val)
            else:
                # If 1 is missing, maybe they start at 1. If 2 missing, probably done.
                # But to be safe (if one is deleted), we continue a bit? 
                # Optimization: stop if we found some keys and hit a miss? 
                # Or just check first 5 slots blindly.
                if i > 3 and not val: 
                    break 
                    
        return list(set(keys)) # Dedup just in case

    def get_openrouter_key(self):
        """
        Fetches the OpenRouter API Key.
        """
        return self.get_secret("openrouter_ai_models_API_KEY")

    def get_stock_news_key(self):
        """
        Fetches the Stock News API Key.
        """
        return self.get_secret("massive_stock_data_API_KEY")

    def get_turso_news_credentials(self):
        """
        Fetches Turso News DB credentials.
        Returns: (db_url, auth_token)
        """
        db_url = self.get_secret("turso_emadarshadalam_newsdatabase_DB_URL")
        auth_token = self.get_secret("turso_emadarshadalam_newsdatabase_AUTH_TOKEN")
        
        # Helper: Ensure compatibility (libsql:// -> https://)
        if db_url and "libsql://" in db_url:
            db_url = db_url.replace("libsql://", "https://")
            
        return db_url, auth_token

    def get_turso_analyst_credentials(self):
        """
        Fetches Turso Analyst DB credentials.
        Returns: (db_url, auth_token)
        """
        db_url = self.get_secret("turso_emadprograms_analystworkbench_DB_URL")
        auth_token = self.get_secret("turso_emadprograms_analystworkbench_AUTH_TOKEN")
        
        if db_url and "libsql://" in db_url:
            db_url = db_url.replace("libsql://", "https://")
            
        return db_url, auth_token
