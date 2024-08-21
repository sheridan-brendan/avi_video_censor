#!/bin/bash

 
ffmpeg -i penii_3-samp.mp4 -i potato_head_test_pattern.png \
    -filter_complex "null[out];
      [out][1:v] overlay=0:0:enable='between(t,4,5)'" \
        -map 0:a -c:a copy blur.mp4 
