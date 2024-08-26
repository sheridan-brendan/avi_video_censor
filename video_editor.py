#!/usr/bin/python3

import subprocess
import shlex
import pandas as pd
from video_indexer_uploader import *


def timestamp_to_seconds(timestamp_str) -> float:
    h, m, s = timestamp_str.split(':')
    seconds = int(h)*3600+int(m)*60+float(s)
    return seconds

def merge_intervals(intervals):
    intervals.sort(key=lambda x: x[0])
    merged = []
    for interval in intervals:
        if not merged or merged[-1][1] < interval[0]:
            merged.append(interval)
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], interval[1]))
    print(merged[:])
    return merged

def find_audio(access_token, account_id, location, video_id) -> list :
    bad_audio = []
    textual = get_textual_artifact(access_token, account_id, location, video_id)
    for word in textual['TextualContentModeration']:
        for instance in word['Instances']:
            if instance['Type'] == "Transcript":
                start = timestamp_to_seconds(instance['Start'])
                end = timestamp_to_seconds(instance['End'])
                bad_audio.append((start,end))
    return merge_intervals(bad_audio)

def bleep_audio(access_token, account_id, location, video_id, video_name,
                video_ext) -> str :
    bad_audio = find_audio(access_token, account_id, location, video_id)
    video_path = f"{video_name}.{video_ext}"
    ffmpeg_call = f"ffmpeg -i {video_path} -vcodec copy -af \"volume=enable='"
    bleeped_path = f"{video_name}-bleeped.{video_ext}"
    for start,end in bad_audio :            
        if ffmpeg_call[-1] == ')':
            ffmpeg_call += "+"
        ffmpeg_call += f"between(t,{start},{end})"
    
    if ffmpeg_call[-1] != ')':
        print("No bleeping necessary")
        return video_name

    ffmpeg_call += f"':volume=0\" {bleeped_path}"
    print(ffmpeg_call)
    subprocess.run(shlex.split(ffmpeg_call))
    return f"{video_name}-bleeped"

def find_bad_chat(textual, vid_start, vid_end, cbuffer=1.0) -> list:
    bad_chat = []
    for word in textual['TextualContentModeration']:
        for instance in word['Instances']:
            if instance['Type'] == "Ocr":
                start = timestamp_to_seconds(instance['Start'])
                end = timestamp_to_seconds(instance['End'])
                bad_chat.append((max(vid_start,start-cbuffer),
                                 min(vid_end,end+cbuffer)))
    return merge_intervals(bad_chat)

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
    cbuffer = binwidth/2*fps
    over_bins = binned[binned['Score'] > agg_threshold]
    bad_bins = []
    for index, row in over_bins.iterrows():
        bad_bins.append((max(min_val,index.left-cbuffer),
                         min(max_val,index.right+cbuffer)))
    return merge_intervals(bad_bins)

def make_visual_filter(bad_bins) -> str:
    if(not bad_bins):
        return "[chatout]null[visout];"

    ffmpeg_filter = "[chatout][1:v] overlay=0:0:enable="

    between = "'"
    for start,end in bad_bins:
        if between[-1] == ')':
            between += "+"
        between += f"between(n,{start},{end})"
    between += "'"
    
    ffmpeg_filter += between
    ffmpeg_filter += "[visout];"
    return ffmpeg_filter


def find_breaks(insights, break_phrase) -> list:
    breaks = []
    for ocr in insights['videos'][0]['insights']['ocr'] :
        if(ocr['text'] == break_phrase) :
            for instance in ocr['instances'] :
                #print (f"start:{instance['start']}, end:{instance['end']}")
                breaks.append((timestamp_to_seconds(instance['start']), 
                               timestamp_to_seconds(instance['end'])))
    return merge_intervals(breaks)

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
        if(start != 0):
            ffmpeg_filter += ";"
        ffmpeg_filter += f"[v{i}]trim=start={start}:end={breaks[i][0]}"
        if(start != 0):
            ffmpeg_filter += f",setpts=PTS-STARTPTS"
        ffmpeg_filter += f"[tv{i}]"
        ffmpeg_filter += f";[0:a]atrim=start={start}:end={breaks[i][0]}"
        if(start != 0):
            ffmpeg_filter += f",asetpts=PTS-STARTPTS"
        ffmpeg_filter += f"[ta{i}]"
        start = breaks[i][1]
    ffmpeg_filter += f";[v{len(breaks)}]trim=start={start}"
    ffmpeg_filter += f",setpts=PTS-STARTPTS[tv{len(breaks)}];"
    ffmpeg_filter += f"[0:a]atrim=start={start}"
    ffmpeg_filter += f",asetpts=PTS-STARTPTS[ta{len(breaks)}];"
    for i in range(len(breaks)+1):
        ffmpeg_filter += f"[tv{i}][ta{i}]"
    ffmpeg_filter += f"concat=n={len(breaks)+1}:a=1[outv][outa]"
    return ffmpeg_filter


def censor_video(access_token, account_id, location, video_id, video_name,
                 video_ext, image, binwidth = 5.0, threshold = .4, chatx
                 = 1100, chaty = 250, chatoffx = 415, chatoffy = 875, blur = 20
                 , break_phrase = "TAKING SHORT BREAK, STAY TUNED!") -> str :
   
    censored_path = f"{video_name}-censored.{video_ext}"
    video_path = f"{video_name}.{video_ext}" 

    #TODO: think of ways to make chat blur less brittle
    visual = get_visual_artifact(access_token, account_id, location, video_id)
    bad_bins = bin_avi_artifact(visual, binwidth, threshold)
    #pd.set_option('display.max_rows', None)
    #print(bad_bins)

    insights = get_insights(access_token, account_id, location, video_id)
    textual = get_textual_artifact(access_token, account_id, location, video_id) 
    
    vid_start = timestamp_to_seconds(insights['videosRanges'][0]['range']['start'])
    vid_end = timestamp_to_seconds(insights['videosRanges'][0]['range']['end'])
    bad_chat = find_bad_chat(textual,vid_start,vid_end)

    breaks = find_breaks(insights, break_phrase)
    #breaks = []

    ##TODO: may need to remove this to not break concat step for files over 2GB
    #if(bad_bins.empty and not bad_chat and not breaks):
    #    print("Nothing to do. Skipping reencode.")
    #    return video_name

    #TODO: consider -crf (18? def=23) option for quality tuning
    ffmpeg_call  = f"ffmpeg -i {video_path} -i {image} -map_chapters -1 "
    ffmpeg_call += f"-filter_complex \""
    
    ffmpeg_call += make_chat_filter(bad_chat, chatx, chaty, chatoffx, chatoffy,
                                    blur)
    ffmpeg_call += make_visual_filter(bad_bins)
    ffmpeg_call += make_break_filter(breaks)

    ffmpeg_call += f"\" -map [outv] -map [outa] {censored_path}"
    print(ffmpeg_call)
    subprocess.run(shlex.split(ffmpeg_call))
    return f"{video_name}-censored"

