"""Run locally once with Google OAuth Desktop client credentials."""
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

parser=argparse.ArgumentParser()
parser.add_argument("--client", default="credentials.json")
parser.add_argument("--output", default="token.json")
args=parser.parse_args()
flow=InstalledAppFlow.from_client_secrets_file(args.client, ["https://www.googleapis.com/auth/calendar.events"])
creds=flow.run_local_server(port=0)
with open(args.output,"w") as f:
    f.write(creds.to_json())
print("Saved token to",args.output)
