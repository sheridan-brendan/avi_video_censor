#!/bin/bash

outfile="${1%.*}"

ffmpeg -i $1 -ss 300 -t 00:00:30 $outfile-samp.mp4
