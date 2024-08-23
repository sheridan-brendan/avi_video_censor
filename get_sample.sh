#!/bin/bash

outfile="${1%.*}"

ffmpeg -i $1 -ss 300 -t 00:00:30 $outfile-samp.mp4
ffmpeg -ss 300 -i $1 -t 00:00:30 $outfile-insamp.mp4
