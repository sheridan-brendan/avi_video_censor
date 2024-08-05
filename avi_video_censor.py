#!/usr/bin/python3

import datetime
from video_indexer_uploader import *


def timestamp_to_seconds(timestamp_str):
    """Converts a timestamp string in HH:MM:SS.ffffff format to seconds.
    
    Args:
      timestamp_str: The timestamp string to convert.
    
    Returns:
      The total number of seconds represented by the timestamp.
    """
    
    time_obj = datetime.datetime.strptime(timestamp_str, "%H:%M:%S.%f")
    seconds_since_midnight = (time_obj - datetime.datetime(1900, 1, 1)).total_seconds()
    return seconds_since_midnight

# Read account details from account_info.txt
#TODO replace with .env?
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
textual = get_textual_artifact_async(access_token, account_id, location, video_id)

#print (textual['TextualContentModeration'][0]['Word'])
#TODO: consider blurring chat for type = ocr
for word in textual['TextualContentModeration']:
    for instance in word['Instances']:
        if instance['Type'] == "Transcript":
            start = timestamp_to_seconds(instance['Start'])
            end = timestamp_to_seconds(instance['End'])
            print(start, end)
