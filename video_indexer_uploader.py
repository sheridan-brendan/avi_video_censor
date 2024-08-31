#!/usr/bin/python3

import requests
import os
import json
import sys
import time

def get_access_token(subscription_key, account_id, location):
    url = f"https://api.videoindexer.ai/Auth/trial/Accounts/{account_id}/AccessToken?allowEdit=true"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def upload_local_file(access_token, account_id, location, video_path) -> str:

    video_name = os.path.basename(video_path)
    url = f"https://api.videoindexer.ai/{location}/Accounts/{account_id}/Videos"

    privacy='private'
    params = {
            'accessToken': access_token,
            'name': video_name,
            'privacy': privacy
    }

    with open(video_path, 'rb') as video_file:
        files = {'file': video_file}
        response = requests.post(url, params=params, files=files)

    #TODO: investigate 409 Client Error response here
    #   possibly related to uploading same video multiple times
    response.raise_for_status()

    video_id = response.json().get('id')
    print(f"finished uploading, id = {video_id}")
    return video_id

def wait_for_index(subscription_key, account_id, location, video_id:str, language:str='English'):
    
    url = f'https://api.videoindexer.ai/{location}/Accounts/{account_id}/' + \
        f'Videos/{video_id}/Index'
    included_insights = "blocks" #empty queries all insights

    params = {
        'accessToken': "",
        'language': language,
        'includedInsights': included_insights,
        'includeSummarizedInsights': False
    }

    print(f'Checking if video {video_id} has finished indexing...')
    processing = True
    while processing:
        params['accessToken'] = get_access_token(subscription_key, account_id, location)
        response = requests.get(url, params=params)

        response.raise_for_status()

        video_result = response.json()
        video_state = video_result.get('state')
        video_progress = video_result['videos'][0]['processingProgress']

        if video_state == 'Processed':
            processing = False
            print(f'The video index for video ID {video_id} has completed.')
            break
        elif video_state == 'Failed':
            processing = False
            print(f"The video index failed for video ID {video_id}.")
            break

        print(f'Processing : {video_progress}')
        time.sleep(60) # wait 60 seconds before checking again

    return params['accessToken']
def get_insights(access_token, account_id, location, video_id:str, language:str='English') -> json:
    url = f'https://api.videoindexer.ai/{location}/Accounts/{account_id}/' + \
        f'Videos/{video_id}/Index'
    included_insights = "transcript,visualContentModeration,ocr"

    params = {
        'accessToken': access_token,
        'language': language,
        'includedInsights': included_insights,
        'includeSummarizedInsights': False
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    video_result = response.json()

    #print(f'Writing json to {video_id}.json')
    #with open(f'{video_id}.json', 'w', encoding='utf-8') as f:
    #    json.dump(video_result, f, ensure_ascii=False, indent=4)
    
    return video_result

def get_textual_artifact(access_token, account_id, location, video_id:str, language:str='English') -> json:
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
    #print(f'Writing textual content moderation json to {video_id}_text.json')
    #with open(f'{video_id}_text.json', 'w', encoding='utf-8') as f:
    #    json.dump(artifact_response.json(), f, ensure_ascii=False, indent=4)
    
    return artifact_response.json()

def get_visual_artifact(access_token, account_id, location, video_id:str, language:str='English') -> json:
    url = f'https://api.videoindexer.ai/{location}/Accounts/{account_id}/' + \
        f'Videos/{video_id}/ArtifactUrl?type=VisualContentModeration'

    params = {
        'accessToken': access_token,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    artifact_url = response.json()
    artifact_response = requests.get(artifact_url, params=params)
    artifact_response.raise_for_status()
    #print(f'Writing visual content moderation json to {video_id}_visual.json')
    #with open(f'{video_id}_visual.json', 'w', encoding='utf-8') as f:
    #    json.dump(artifact_response.json(), f, ensure_ascii=False, indent=4)
    
    return artifact_response.json()

