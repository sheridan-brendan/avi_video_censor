## avi_video_censor
This is a bare-bones prototype for automated video censoring of cursing/graphic content/dead air/ect. using azure video indexer insights. The motivating use case is censoring Twitch gameplay vods for upload to youtube.

## Requirements
* `python3` - see [requirements](./requirements.txt) for python libraries and versions
* `ffmpeg` - installed and available from call PATH
* `Azure AI Video Indexer` - account with API subscription, see [Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-video-indexer/video-indexer-use-apis) for signup instructions

## Setup
* Populate a file, `account_info.txt` in the script directory with your Azure Video indexer account keys and location (or 'trial' for a trial account) using the following format - 

`<account id>`\
`<subscription key>`\
`<location>`

AVI keys can be found on your [profile](https://api-portal.videoindexer.ai/profile)

* Create an image with the same dimensions as your video, to be overlayed over graphic content.
* Adjust default values in `avi_video_censor.py` to match your streaming overlay if applicable (`chatx` and `chaty` should correspond to the dimensions of your chat box, `chatoffx` and `chatoffy` should correspond to its offset. `break_phrases` should be populated with identitifying text from any break/intro/outro cards. `threshold` can be adjusted between 0.0 and 3.0 as necessary - lower values result in more video censorship)

## Usage
* Call with: `avi_video_censor <video_file.ext> <censor_image>`
