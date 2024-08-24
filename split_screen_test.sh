#!/bin/bash


mpv penii_3-samp.mp4 --external-file=penii_3-insamp.mp4 --lavfi-complex='[vid1] [vid2] hstack [vo]'
