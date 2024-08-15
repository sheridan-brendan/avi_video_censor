#!/bin/bash

 
ffmpeg -i penii_3-samp.mp4 -filter_complex \
    "[0:v]crop=1100:250:415:875,avgblur=20:enable='between(t,5,7)'[fg]; 
    [0:v][fg]overlay=415:875:enable='between(t,5,7)'[v]" \
        -map "[v]" -map 0:a -c:a copy blur.mp4 -y
