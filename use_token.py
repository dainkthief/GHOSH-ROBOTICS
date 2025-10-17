from kiteconnect import KiteConnect
import json

api_key = "1u9tjt5sxp6ewroe"

with open("access_token.json") as f:
    token_data = json.load(f)

kite = KiteConnect(api_key=api_key)
kite.set_access_token(token_data["access_token"])

print("Token valid. Example quote:\n")
print(kite.quote("NSE:INFY"))
