#!/usr/bin/python3

from video_indexer_uploader import *
from video_editor import *

#Read account details from account_info.txt
#TODO: replace with .env?
account_file = open("account_info.txt")
lines = account_file.readlines()
account_id = lines[0].rstrip()
subscription_key = lines[1].rstrip()
location = lines[2].rstrip()

try:
    video_path = sys.argv[1]
    video_name, video_ext = video_path.rsplit('.',1)
    image_path = sys.argv[2]
except ValueError:
    print("Usage: avi_video_censor <video_file.ext> <censor_image>")
    raise

#Visual moderation and chat box values
#TODO: add command line options
binwidth = 5.0 #video frames to aggregate(seconds)
threshold = 0.4 #magic number cutoff normalized to binwidth (0-3.0)
chatx = 1100
chaty = 250
chatoffx = 415
chatoffy = 875
blur = 20


#TODO: considering splitting up file automatically
if os.path.getsize(video_path) > 2e9:
    sys.exit("Error: maximum local upload size 2GB")



access_token = get_access_token(subscription_key, account_id, location)
video_id = upload_local_file(access_token, account_id, location, video_path)
#video_id = "07vwapsjoy" #no offensive content example
#video_id = "21ec4df54e" #offensive content example

access_token = wait_for_index(subscription_key, account_id, location, video_id)
#insights = get_insights(access_token, account_id, location, video_id)
bleeped_name = bleep_audio(access_token, account_id, location, video_id, video_name, video_ext)
#bleeped_name = video_name
censored_name = censor_video(access_token, account_id, location, video_id,
                             bleeped_name, video_ext, image_path, binwidth,
                             threshold, chatx, chaty, chatoffx, chatoffy, blur)

print(f"Censored video: {censored_name}.{video_ext}")
