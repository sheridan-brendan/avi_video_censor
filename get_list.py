#!/usr/bin/python3

import requests
import json
import sys
from pathlib import Path

account_file = Path(__file__).with_name('account_info.txt')
with account_file.open('r') as af: 
    lines = af.readlines()
    account_id = lines[0].rstrip()
    subscription_key = lines[1].rstrip()
    location = lines[2].rstrip()


url = f"https://api.videoindexer.ai/Auth/{location}/Accounts/{account_id}/AccessToken?allowEdit=true"
headers = {
    'Ocp-Apim-Subscription-Key': subscription_key
}
response = requests.get(url, headers=headers)
response.raise_for_status()
access_token = response.json()


url = f"https://api.videoindexer.ai/{location}/Accounts/{account_id}/Videos"

params = {
        'accessToken': access_token,
        'pageSize': 1000 #number of video listings to check
}


response = requests.get(url, params=params)
response.raise_for_status()
print(f'Writing video list json to video_list.json')
with open(f'video_list.json', 'w', encoding='utf-8') as f:
    json.dump(response.json(), f, ensure_ascii=False, indent=4)

