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
    
    if ffmpeg_call[-1] != ')':
        print("No bleeping necessary")
        return video_name

    ffmpeg_call += f"':volume=0\" {bleeped_path}"
    #print(ffmpeg_call)
    subprocess.run(shlex.split(ffmpeg_call))
    return f"{video_name}-bleeped"

def find_bad_chat(textual) -> list:
    bad_chat = []
    for word in textual['TextualContentModeration']:
        for instance in word['Instances']:
            if instance['Type'] == "Ocr":
                start = timestamp_to_seconds(instance['Start'])
                end = timestamp_to_seconds(instance['End'])
                bad_chat.append((start,end))
    return bad_chat

def make_chat_filter(bad_chat, chatx, chaty, chatoffx, chatoffy, blur) -> str:
    if(not bad_chat):
        return "null[chatout];"

    ffmpeg_filter = f"[0:v]crop={chatx}:{chaty}"
    ffmpeg_filter += f":{chatoffx}:{chatoffy},avgblur={blur}:enable="
    
    between = "'"
    for chat in bad_chat :            
        if between[-1] == ')':
            between += "+"
        between += f"between(t,{chat[0]},{chat[1]})"
    between += "'"
    
    ffmpeg_filter += between
    ffmpeg_filter += f"[fg];[0:v][fg]overlay={chatoffx}:{chatoffy}:enable="
    ffmpeg_filter += between
    ffmpeg_filter += f"[chatout];"
    return ffmpeg_filter

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

def make_visual_filter(bad_bins, buffer) -> str:
    if(bad_bins.empty):
        return "[chatout]null[visout];"

    ffmpeg_filter = "[chatout][1:v] overlay=0:0:enable="

    between = "'"
    for index, row in bad_bins.iterrows():
        #print(f"{index.left-buffer},{index.right+buffer}")
        if between[-1] == ')':
            between += "+"
        between += f"between(n,{index.left-buffer},{index.right+buffer})"
    between += "'"
    
    ffmpeg_filter += between
    ffmpeg_filter += "[visout];"
    return ffmpeg_filter


def find_breaks(insights, break_phrase = "TAKING SHORT BREAK, STAY TUNED!") -> list:
    breaks = []
    for ocr in insights['videos'][0]['insights']['ocr'] :
        if(ocr['text'] == break_phrase) :
            for instance in ocr['instances'] :
                #print (f"start:{instance['start']}, end:{instance['end']}")
                breaks.append((timestamp_to_seconds(instance['start']), 
                               timestamp_to_seconds(instance['end'])))
    return breaks

def make_break_filter(breaks) -> str:
    #print(breaks)
    if (not breaks):
        return "[visout]null[outv];[0:a]anull[outa]"
    ffmpeg_filter  = f"[visout]split={len(breaks)+1}"
    for i in range(len(breaks)+1):
        ffmpeg_filter += f"[v{i}]"
    ffmpeg_filter += ";"
    start = 0
    for i in range(len(breaks)):
        ffmpeg_filter += f"[v{i}]trim=start={start}:end={breaks[0][0]}"
        ffmpeg_filter += f",setpts=PTS-STARTPTS[tv{i}];"
        ffmpeg_filter += f"[0:a]atrim=start={start}:end={breaks[0][0]}"
        ffmpeg_filter += f",asetpts=PTS-STARTPTS[ta{i}];"
        start = breaks[0][1]
    ffmpeg_filter += f"[v{len(breaks)}]trim=start={start}"
    ffmpeg_filter += f",setpts=PTS-STARTPTS[tv{len(breaks)}];"
    ffmpeg_filter += f"[0:a]atrim=start={start}"
    ffmpeg_filter += f",asetpts=PTS-STARTPTS[ta{len(breaks)}];"
    for i in range(len(breaks)+1):
        ffmpeg_filter += f"[tv{i}][ta{i}]"
    ffmpeg_filter += "concat=a=1[outv][outa]"
    return ffmpeg_filter


def censor_video(access_token, account_id, location, video_id, video_name,
                 video_ext, image, binwidth = 5.0, threshold = .4, chatx
                 = 1100, chaty = 250, chatoffx = 415, chatoffy = 875, blur = 20) -> str :
   
    censored_path = f"{video_name}-censored.{video_ext}"
    video_path = f"{video_name}.{video_ext}" 

    #TODO: think of ways to make chat blur less brittle
    visual = get_visual_artifact(access_token, account_id, location, video_id)
    bad_bins,buffer = bin_avi_artifact(visual, binwidth, threshold)
    #pd.set_option('display.max_rows', None)
    #print(bad_bins)

    textual = get_textual_artifact(access_token, account_id, location, video_id) 
    bad_chat = find_bad_chat(textual)

    insights = get_insights(access_token, account_id, location, video_id)
    breaks = find_breaks(insights)
    #breaks = []

    if(bad_bins.empty and not bad_chat and not breaks):
        print("Nothing to do. Skipping reencode.")
        return video_name

    #TODO: consider -crf (18? def=23) option for quality tuning
    ffmpeg_call  = f"ffmpeg -i {video_path} -i {image} -map_chapters -1 "
    ffmpeg_call += f"-filter_complex \""
    
    ffmpeg_call += make_chat_filter(bad_chat, chatx, chaty, chatoffx, chatoffy,
                                    blur)
    ffmpeg_call += make_visual_filter(bad_bins,buffer)
    ffmpeg_call += make_break_filter(breaks)

    ffmpeg_call += f"\" -map [outv] -map [outa] {censored_path}"
    print(ffmpeg_call)
    subprocess.run(shlex.split(ffmpeg_call))
    return f"{video_name}-censored"

