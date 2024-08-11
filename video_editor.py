#!/usr/bin/python3

import subprocess
import shlex
import pandas as pd
from video_indexer_uploader import *


def timestamp_to_seconds(timestamp_str) -> str:
    h, m, s = timestamp_str.split(':')
    seconds = str(int(h)*3600+int(m)*60+float(s))
    return seconds

def bleep_audio(access_token, account_id, location, video_id, video_name,
                video_ext) -> str :
    textual = get_textual_artifact(access_token, account_id, location, video_id)
    video_path = f"{video_name}.{video_ext}"
    ffmpeg_call = f"ffmpeg -i {video_path} -vcodec copy -af \"volume=enable='"
    bleeped_path = f"{video_name}-bleeped.{video_ext}"
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
    return f"{video_name}-bleeped"

def censor_video(access_token, account_id, location, video_id, video_name,
                 video_ext, image, binwidth = 5.0, threshold = .5) -> str :
    visual = get_visual_artifact(access_token, account_id, location, video_id)
    fps = visual['Fps']
    df = pd.json_normalize(visual['Results'])
    #df.drop(['isAdultContent','isRacyContent','isGoryContent'], axis=1)
    df.drop(['Adult.isAdultContent','Adult.isRacyContent','Adult.isGoryContent'], 
            axis=1, inplace=True)
    
    df['Score'] = df['Adult.adultScore']+df['Adult.racyScore']+df['Adult.goreScore']
    df.drop(['Adult.adultScore','Adult.racyScore','Adult.goreScore'], axis=1,
            inplace=True)

    min_val,max_val = df['FrameIndex'].iloc[[0, -1]]
    num_bins = int((max_val - min_val) / (binwidth*fps)) + 1
    #print(num_bins)
    df['bins'] = pd.cut(df['FrameIndex'], bins=num_bins)
    binned = df.groupby('bins').sum()
    print(binned)

    agg_threshold = threshold*binwidth
    buffer = binwidth/2*fps
    bad_bins = binned[binned['Score'] > agg_threshold]
    print(bad_bins)
    censored_path = f"{video_name}-censored.{video_ext}"
    video_path = f"{video_name}.{video_ext}" 
    ffmpeg_call = f"ffmpeg -i {video_path} -i {image} "
    ffmpeg_call += f"-filter_complex \"[0:v][1:v] overlay=0:0:enable='"
    for index, row in bad_bins.iterrows():
        #print(f"{index.left-buffer},{index.right+buffer}")
        if ffmpeg_call[-1] == ')':
            ffmpeg_call += "+"
        ffmpeg_call += f"between(n,{index.left-buffer},{index.right+buffer})"

    ffmpeg_call += f"'\" -pix_fmt yuv420p -c:a copy {censored_path}"
    #print(ffmpeg_call)
    subprocess.run(shlex.split(ffmpeg_call))
    return f"{video_name}-censored"

    

