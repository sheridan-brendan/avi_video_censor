#!/bin/bash

outfile="${1%.*}"

ffmpeg -i $1 -ss 300 -t 00:00:30 -vcodec copy $outfile-samp.mp4
ffmpeg -ss 300 -i $1 -t 00:00:30 -vcodec copy $outfile-insamp.mp4
