#!/usr/bin/python3

import subprocess
import shlex
from video_indexer_uploader import *


def timestamp_to_seconds(timestamp_str) -> str:
    h, m, s = timestamp_str.split(':')
    seconds = str(int(h)*3600+int(m)*60+float(s))
    return seconds

# Read account details from account_info.txt
#TODO replace with .env?
account_file = open("account_info.txt")
lines = account_file.readlines()
account_id = lines[0].rstrip()
subscription_key = lines[1].rstrip()
location = lines[2].rstrip()

try:
    video_path = sys.argv[1]
    video_name, video_ext = video_path.rsplit('.',1)
except ValueError:
    print("Usage: avi_video_censor <video_file.ext>")
    raise


access_token = get_access_token(subscription_key, account_id, location)
#video_id = upload_local_file(access_token, account_id, location, video_path)
video_id = "21ec4df54e"
wait_for_index(access_token, account_id, location, video_id)
get_insights(access_token, account_id, location, video_id)
textual = get_textual_artifact(access_token, account_id, location, video_id)

ffmpeg_call = f"ffmpeg -i {video_path} -vcodec copy -af \"volume=enable='"

bleeped_path = f"{video_name}-bleeped.{video_ext}"
print(bleeped_path)

for word in textual['TextualContentModeration']:
    for instance in word['Instances']:
        #TODO: consider blurring chat for type = ocr
        if instance['Type'] == "Transcript":
            start = timestamp_to_seconds(instance['Start'])
            end = timestamp_to_seconds(instance['End'])
            if ffmpeg_call[-1] == ')':
                ffmpeg_call += "+"
            ffmpeg_call += f"between(t,{start},{end})"
ffmpeg_call += f"':volume=0\" {bleeped_path}"
#print(ffmpeg_call)
subprocess.run(shlex.split(ffmpeg_call))
