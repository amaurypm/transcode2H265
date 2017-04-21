# transcode2H265
Unattended video transcoder to H265 and ACC codecs, in MKV containers.

## What does this do?
This program transcode video files to H265 and AAC in MKV format. Subtitles,
if present, are automatically detected and soft subbed into the corresponding
output files.

## How does it work?
transcode2H265 uses ffmpeg, mkmerge and other system tools to convert the input videos.

## How do I install it?
As a python script you can just run the transcode2H265.py file, or put a symbolic link in any directory of your PATH (e.g. /usr/local/bin)
The script needs ffmpeg and mkvtoolnix to work, so, if it can not find them in your system it will complain and exit.

## Do not many similar programs already exist?
Probably, but I use this. I like it and it works well for me, if you like it too, enjoy it.

## How do I use it?
Just do:
`transcode2H265.py video_file[s]`

It has some options (type `transcode2H265 -h` or see below), but defaults should work in most cases.

### Options
```
positional arguments:
  video                 Input video file(s).

optional arguments:
  -h, --help            Show this help message and exit.
  -p PRESET, --preset PRESET
                        X265 preset [default: medium].
  -q CRF, --crf CRF     CRF value [default: 28]. Determines the output video
                        quality. Smaller values gives better qualities and
                        bigger file sizes, bigger values result in less
                        quality and smaller file sizes. Default value results
                        in a nice quality/size ratio. CRF values should be in
                        the range of 1 to 50.
  -r, --replace-original-video-file
                        If set then original video files will be erased after
                        transcoding. WARNING: deleted files can not be easily
                        recovered!
  -l AVLANG, --avlang AVLANG
                        Default audio language for MKV files obtained (used
                        only if the original stream languages fail to be
                        determined) [default: eng].
  -L SLANG, --slang SLANG
                        Default subtitle language of soft-subbed subtitles
                        (only used if original subtitle languages fail to be
                        determined) [default: spa].
  -x FILENAME_POSTFIX, --filename-postfix FILENAME_POSTFIX
                        Postfix to be added to newly created H.265 video files
                        [default: _h265].
  -t THREADS, --threads THREADS
                        Indicates the number of processor cores the script
                        will use. 0 indicates to use as many as possible
                        [default: 0].
  -c, --auto-crop       Turn on autocrop function. WARNING: Use with caution
                        as some video files has variable width horizontal (and
                        vertical) black bars, in those cases you will probably
                        lose data.
  -v, --version         Show program's version number and exit.
```

## Is it just in English?
In English and Spanish, depending of your locale. I just speak this two languages, so, if you like it in other, you can always contribute...

