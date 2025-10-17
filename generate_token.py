from kiteconnect import KiteConnect
import json

api_key = "1u9tjt5sxp6ewroe"
api_secret = "gdlp4sdwdtc30ugip6ap98r6622ddy5y"

kite = KiteConnect(api_key=api_key)

print("\n1️⃣  Open this URL in your mobile browser and log in:")
print(kite.login_url())
print("\nAfter login, copy the 'request_token' from the address bar and paste below.\n")

request_token = input("Enter request_token: ").strip()

data = kite.generate_session(request_token, api_secret=api_secret)
access_token = data["access_token"]

with open("access_token.json", "w") as f:
    json.dump({"access_token": access_token}, f)

print("\n✅ Access token saved to access_token.json")
