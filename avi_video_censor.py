#!/usr/bin/python3

from video_indexer_uploader import *
from video_editor import *
import csv

#Read account details from account_info.txt
#TODO: replace with .env?
account_file = open("account_info.txt")
lines = account_file.readlines()
account_id = lines[0].rstrip()
subscription_key = lines[1].rstrip()
location = lines[2].rstrip()
account_file.close()

#TODO: doesn't handle filenames with spaces
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
blur = 20
#Amnesia example
chatx = 1100
chaty = 250
chatoffx = 415
chatoffy = 875
break_phrase = "TAKING SHORT BREAK, STAY TUNED!"

files = []
video_size=os.path.getsize(video_path)
if video_size > 2e9:
    video_len=float(subprocess.check_output(shlex.split(f"ffprobe -v error\
            -show_entries format=duration -of\
            default=noprint_wrappers=1:nokey=1 {video_path}")))
    approx_bytrate=video_size/video_len
    approx_len=1e9/approx_bytrate
    segment_file=f"{video_name}.csv"
    subprocess.run(shlex.split(f"ffmpeg -i {video_path} -map 0 -c copy\
            -f segment -segment_time {approx_len} -segment_list\
            {segment_file} -reset_timestamps 1 {video_name}_%02d.{video_ext}"))
    with open(segment_file, mode='r') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader :
            files.append(row[0])

else :
    files.append(video_name)

print(files[:])

for i, path in enumerate(files):
    video,ext = video_path.rsplit('.',1)
    access_token = get_access_token(subscription_key, account_id, location)
    video_id = upload_local_file(access_token, account_id, location, path)
    #video_id = "07vwapsjoy" #no offensive content example
    #video_id = "21ec4df54e" #offensive content example
    #video_id = "b81850331b" #2nd offensive example

    access_token = wait_for_index(subscription_key, account_id, location, video_id)
    #insights = get_insights(access_token, account_id, location, video_id)
    bleeped_name = bleep_audio(access_token, account_id, location, video_id, 
                               video, video_ext)
    #bleeped_name = video
    censored_name = censor_video(access_token, account_id, location, video_id,
                                 bleeped_name, video_ext, image_path, binwidth,
                                 threshold, chatx, chaty, chatoffx, chatoffy,
                                 blur, break_phrase)
    
    files[i] = censored_name
    print(f"Censored video: {censored_name}.{video_ext}")

processed_file = "error"
if(len(files) == 1):
    processed_file = f"{files[0]}.{video_ext}"
else:
    processed_file = f"{video_name}-censored.{video_ext}"
    catfile = f"{video_name}.ffcat"
    f = open(catfile, "w")
    for filename in files :
        f.write(f"file '{filename}'\n")
    f.close()
    subprocess.run(shlex.split(f"ffmpeg -f concat -safe 0 -i {catfile}\
            -c copy {processed_file}"))

print(f"Final video: {processed_file}")
