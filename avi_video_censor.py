#!/usr/bin/python3

from video_indexer_uploader import *
from video_editor import *
from pathlib import Path
import csv

#Read account details from account_info.txt
#TODO: replace with .env?
account_file = Path(__file__).with_name('account_info.txt')
with account_file.open('r') as af:
    lines = af.readlines()
    account_id = lines[0].rstrip()
    subscription_key = lines[1].rstrip()
    location = lines[2].rstrip()

try:
    video_path = Path(sys.argv[1])
    video_name = video_path.with_suffix('')
    video_ext = video_path.suffix
    image_path = Path(sys.argv[2])
except (ValueError,IndexError):
    print("Usage: avi_video_censor <video_file.ext> <censor_image>")
    raise

#Visual moderation and chat box values
#TODO: add command line options
binwidth = 5.0 #video frames to aggregate(seconds)
threshold = 0.9 #magic number cutoff normalized to binwidth (0-3.0)
blur = 20
#Amnesia example
chatx = 1100
chaty = 250
chatoffx = 415
chatoffy = 875
break_phrases = {'TAKING SHORT BREAK, STAY TUNED!', 'WELCOME TO THE STREAM!'}

files = []
video_size=video_path.stat().st_size
if video_size > 2e9:
    video_len=float(subprocess.check_output(shlex.split(f"ffprobe -v error\
            -show_entries format=duration -of\
            default=noprint_wrappers=1:nokey=1 '{video_path}'")))
    approx_bytrate=video_size/video_len
    approx_len=1e9/approx_bytrate
    segment_file=Path(f"{video_name}.csv")
    subprocess.run(shlex.split(f"ffmpeg -i '{video_path}' -map 0 -c copy\
            -f segment -segment_time {approx_len} -segment_list\
            '{segment_file}' -reset_timestamps 1 '{video_name}_%02d{video_ext}'"))
    with segment_file.open('r') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader :
            files.append(Path(row[0]))
    Path.unlink(segment_file)
else :
    files.append(video_path)

print(files[:])

video_ids = []
#TODO: consider script-level parallelization here for better resilience to 
#   resource bottlenecks
for path in files:
    access_token = get_access_token(subscription_key, account_id, location)
    video_id = upload_local_file(access_token, account_id, location, path)
    video_ids.append(video_id)

for i, path in enumerate(files):
    video = path.with_suffix('')
    ext = path.suffix
    video_id = video_ids[i]
    access_token = wait_for_index(subscription_key, account_id, location, video_id)
    bleeped_name = bleep_audio(access_token, account_id, location, video_id, video, video_ext)
    #bleeped_name = video
    censored_name = censor_video(access_token, account_id, location, video_id,
                                 bleeped_name, video_ext, image_path, binwidth,
                                 threshold, chatx, chaty, chatoffx, chatoffy,
                                 blur, break_phrases)
    
    #CLEANUP intermediate files
    if(bleeped_name != video) :
        Path.unlink(Path(f"{bleeped_name}{ext}"))
    if(len(files) > 1) :
        Path.unlink(path)

    files[i] = Path(f"{censored_name}{video_ext}")
    print(f"Censored video: {files[i]}")

processed_file = "error"
if(len(files) == 1):
    processed_file = f"{files[0]}"
else:
    processed_file = f"{video_name}-censored{video_ext}"
    cat_path = Path(f"{video_name}.ffcat")
    with cat_path.open('w') as cf:
        for path in files :
            cf.write(f"file '{path}'\n")
    
    subprocess.run(shlex.split(f"ffmpeg -f concat -safe 0 -i '{cat_path}'\
            -c copy '{processed_file}'"))
    #CLEANUP partial files
    Path.unlink(cat_path)
    for path in files :
        Path.unlink(path)

print(f"Final video: {processed_file}")
