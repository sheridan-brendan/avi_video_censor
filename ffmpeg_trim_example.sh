#!/bin/bash

 
ffmpeg -i penii_3-samp.mp4 -i potato_head_test_pattern.png -map_chapters -1 \
    -filter_complex\
    "[0:v]trim=start=1:end=15,setpts=PTS-STARTPTS[av];
     [0:a]atrim=start=1:end=15,asetpts=PTS-STARTPTS[aa];
     [0:v]trim=start=20:end=25,setpts=PTS-STARTPTS[bv];
     [0:a]atrim=start=20:end=25,asetpts=PTS-STARTPTS[ba];
     [av][aa][bv][ba]concat=a=1[outv][outa]" \
        -map [outv] -map [outa] trim.mp4

