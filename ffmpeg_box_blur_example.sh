#!/bin/bash

 
ffmpeg -i penii_3-samp.mp4 -i potato_head_test_pattern.png \
    -filter_complex\
    "[0:v]crop=1100:250:415:875,avgblur=20:
     enable='between(t,4,7)'[fg]; 
     [0:v][fg]overlay=415:875:
     enable='between(t,4,7)'[out];
     [out][1:v] overlay=0:0:enable='between(t,4,5)'" \
        -map 0:a -c:a copy blur.mp4 -y
