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

def bin_avi_artifact(visual, binwidth, threshold) -> list:
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
    #print(binned)

    agg_threshold = threshold*binwidth
    buffer = binwidth/2*fps
    bad_bins = binned[binned['Score'] > agg_threshold]
    return [bad_bins,buffer]


def censor_video(access_token, account_id, location, video_id, video_name,
                 video_ext, image, binwidth = 5.0, threshold = .4, chatx
                 = 1100, chaty = 250, chatoffx = 415, chatoffy = 875, blur = 20) -> str :
    
    visual = get_visual_artifact(access_token, account_id, location, video_id)
    bad_bins,buffer = bin_avi_artifact(visual, binwidth, threshold)
    pd.set_option('display.max_rows', None)
    print(bad_bins)
    censored_path = f"{video_name}-censored.{video_ext}"
    video_path = f"{video_name}.{video_ext}" 
    textual = get_textual_artifact(access_token, account_id, location, video_id) 

    ffmpeg_call  = f"ffmpeg -i {video_path} -i {image} "
    ffmpeg_call += f"-filter_complex \""
    ffmpeg_call += f"[0:v]crop={chatx}:{chaty}"
    ffmpeg_call += f":{chatoffx}:{chatoffy},avgblur={blur}:enable="
    
    between = "'"
    for word in textual['TextualContentModeration']:
        for instance in word['Instances']:
            if instance['Type'] == "Ocr":
                start = timestamp_to_seconds(instance['Start'])
                end = timestamp_to_seconds(instance['End'])
                if between[-1] == ')':
                    between += "+"
                between += f"between(t,{start},{end})"
    between += "'"
    ffmpeg_call += between
    
    if(len(bad_bins) == 0 and between == "''"):
        print("No video censoring necessary.")
        return vide_name

    ffmpeg_call += f"[fg];[0:v][fg]overlay={chatoffx}:{chatoffy}:enable="
    ffmpeg_call += between
    ffmpeg_call += f"[out];[out][1:v] overlay=0:0:enable='"

    for index, row in bad_bins.iterrows():
        #print(f"{index.left-buffer},{index.right+buffer}")
        if ffmpeg_call[-1] == ')':
            ffmpeg_call += "+"
        ffmpeg_call += f"between(n,{index.left-buffer},{index.right+buffer})"

    ffmpeg_call += f"'\" -map 0:a -c:a copy {censored_path}"
    print(ffmpeg_call)
    subprocess.run(shlex.split(ffmpeg_call))
    return f"{video_name}-censored"

    

