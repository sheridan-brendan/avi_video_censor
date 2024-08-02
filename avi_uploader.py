#!/usr/bin/python3

import requests
import os
import time
import json
import sys

def get_access_token_async(subscription_key, account_id, location):
    url = f"https://api.videoindexer.ai/Auth/trial/Accounts/{account_id}/AccessToken?allowEdit=true"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def upload_local_file_async(access_token, account_id, location, video_path) -> str:

    video_name = os.path.basename(video_path)
    url = f"https://api.videoindexer.ai/{location}/Accounts/{account_id}/Videos"

    privacy='private'
    #partition=''
    #video_description:str=''
    params = {
            'accessToken': access_token,
            'name': video_name,
            #'description': video_description,
            'privacy': privacy#,
            #'partition': partition
    }

    with open(video_path, 'rb') as video_file:
        files = {'file': video_file}
        response = requests.post(url, params=params, files=files)

    response.raise_for_status()

    #if response.status_code == 200:
    #    print(f"Video '{video_name}' uploaded successfully.")
    #else:
    #    print(f"Request failed with status code: {response.StatusCode}")
    #    print(f"Error uploading video: {response.text}")
    video_id = response.json().get('id')
    return video_id

def wait_for_index_async(access_token, account_id, location, video_id:str, language:str='English') -> None:
    
    url = f'https://api.videoindexer.ai/{location}/Accounts/{account_id}/' + \
        f'Videos/{video_id}/Index'
    included_insights = "blocks" #empty queries all insights

    params = {
        'accessToken': access_token,
        'language': language,
        'includedInsights': included_insights,
        'includeSummarizedInsights': False
    }

    print(f'Checking if video {video_id} has finished indexing...')
    processing = True
    #start_time = time.time()
    #TODO: token may time out here for large files
    while processing:
        response = requests.get(url, params=params)

        response.raise_for_status()

        video_result = response.json()
        video_state = video_result.get('state')
        video_progress = video_result['videos'][0]['processingProgress']

        if video_state == 'Processed':
            processing = False
            print(f'The video index for video ID {video_id} has completed.')
            #print(f'Writing json to {video_id}.json')
            #with open(f'{video_id}.json', 'w', encoding='utf-8') as f:
            #    json.dump(video_result, f, ensure_ascii=False, indent=4)
            break
        elif video_state == 'Failed':
            processing = False
            print(f"The video index failed for video ID {video_id}.")
            break

        print(f'Processing : {video_progress}')
        time.sleep(30) # wait 30 seconds before checking again

def get_insights_async(access_token, account_id, location, video_id:str, language:str='English'):
    url = f'https://api.videoindexer.ai/{location}/Accounts/{account_id}/' + \
        f'Videos/{video_id}/Index'
    included_insights = "transcript,visualContentModeration"

    params = {
        'accessToken': access_token,
        'language': language,
        'includedInsights': included_insights,
        'includeSummarizedInsights': False
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    video_result = response.json()

    print(f'Writing json to {video_id}.json')
    with open(f'{video_id}.json', 'w', encoding='utf-8') as f:
        json.dump(video_result, f, ensure_ascii=False, indent=4)

def get_textual_artifact_async(access_token, account_id, location, video_id:str, language:str='English'):
    url = f'https://api.videoindexer.ai/{location}/Accounts/{account_id}/' + \
        f'Videos/{video_id}/ArtifactUrl?type=TextualContentModeration'

    params = {
        'accessToken': access_token,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    artifact_url = response.json()
    artifact_response = requests.get(artifact_url, params=params)
    artifact_response.raise_for_status()
    print(f'Writing textual content moderation json to {video_id}_text.json')
    with open(f'{video_id}_text.json', 'w', encoding='utf-8') as f:
        json.dump(artifact_response.json(), f, ensure_ascii=False, indent=4)
    


# Read account details from account_info.txt
account_file = open("account_info.txt")
lines = account_file.readlines()
account_id = lines[0].rstrip()
subscription_key = lines[1].rstrip()
location = lines[2].rstrip()
video_path = sys.argv[1]
access_token = get_access_token_async(subscription_key, account_id, location)
#video_id = upload_local_file_async(access_token, account_id, location, video_path)
video_id = "21ec4df54e"
wait_for_index_async(access_token, account_id, location, video_id)
get_insights_async(access_token, account_id, location, video_id)
get_textual_artifact_async(access_token, account_id, location, video_id)
