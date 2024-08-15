#!/bin/bash

outfile="${1%.*}"

ffmpeg -i $1 -acodec copy -vcodec copy -ss 300 -t 00:00:10 $outfile-samp.mp4
