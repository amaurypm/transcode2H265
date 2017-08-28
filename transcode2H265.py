#!/usr/bin/env python3
# -*- coding: utf-8 -*-
## A wrapper script to transcode video files to H265, AAC in MKV format, using
## ffmpeg and mkvmerge.
##
## Amaury Pupo Merino
## amaury.pupo@gmail.com
## December 2015
## Ported to python3 in November 2016.
## Internationalization support added in November 2016 (Starting with "es").
## Change old % based string format for .format() (November 2016)
## Substitute optparse by argparse (November 2016)
## Bugfixes in December 2016.
## Updates of ffmpeg instructions in December 2016.
##
## This script is released under GPL v3.
##

## Importing modules
import sys
import os
import time
import random
import subprocess
import gettext
import string

## Setting internationalization
localedir = os.path.join(os.path.abspath(os.path.dirname(os.path.realpath(__file__))), 'locale')

translate = gettext.translation('transcode2H265', localedir, fallback=True)

_ = translate.gettext

def i18n_text_argparse(text):
    text = text.replace("usage", _("usage"))
    text = text.replace("positional arguments", _("positional arguments"))
    text = text.replace("optional arguments", _("optional arguments"))
    #text = text.replace("show this help message and exit",
    #                    _("show this help message and exit"))
    text = text.replace("error", _("error"))
    text = text.replace("the following arguments are required",
                        _("the following arguments are required"))
    text = text.replace("unrecognized arguments",
                        _("unrecognized arguments"))
    text = text.replace("too few arguments",
                        _("too few arguments"))
    #text = text.replace("show program's version number and exit", 
    #        _("show program's version number and exit")) # Internationalization does not work with this message. I don't know why.
    text = text.replace("expected one argument",_("expected one argument"))
    return text

gettext.gettext = i18n_text_argparse

import argparse ## Need to be imported after the previous declarations, to allow argparse text be translated.


## Classes
class Video:
    """Contains actual and proposed video information, and can transforme itself.
    
    """
    def __init__(self,filename):
        self.__in_filename=filename       
        self.__in_ok=False
        self.__in_duration=None
        self.__avlang = None
        self.__preset=None        
        self.__CRF=None
        self.__ext_sub_files=[] # Now a list, for more than one sub files. This files are always kept.
        self.__int_sub_files=[] # Now a list, for more than one sub files. This files are removed after the script is completed.
        self.__sub_charsets={} # Now a dictionary, with each subfile as a key.
        self.__sub_exts=['.srt','.ass','.ssa','.txt']        
        self.__default_avlang='eng'
        self.__default_slang='spa'        
        self.__slangs = {} # To support multiple subtitles.
        self.__ffmpeg_output_ext='.mkv'
        self.__ffmpeg_output_postfix='_tmp_' + random_string(10)
        self.__ffmpeg_output=os.path.splitext(self.__in_filename)[0]+self.__ffmpeg_output_postfix+self.__ffmpeg_output_ext
        self.__replace_original=False
        self.__output_postfix=None
        self.__threads=None
        self.__crop_data=None
        self.__get_input_data()

    def __get_input_data(self):
        if os.path.isfile(self.__in_filename):
            cproc = subprocess.run(["ffmpeg", "-i", self.__in_filename], stdout = subprocess.DEVNULL, stderr = subprocess.PIPE, universal_newlines = True)
            for line in cproc.stderr.split('\n'):
                line=line.strip()
                if ('Video' in line) and ('Stream' in line):
                    if 'ansi' not in line:
                        self.__in_ok=True
                    
                if ('Audio' in line) and ('Stream' in line):
                    if '(' in line.split(':')[1]:
                        self.__avlang = line.split(':')[1].split('(')[1].strip(')')
                        if "unk" in self.__avlang.lower() or "und" in self.__avlang.lower():
                            self.__avlang = None
                    
                if 'Duration' in line:
                    duration_string=line.split(',')[0].split()[1]
                    if not 'N/A' in duration_string:
                        self.__in_duration=dstring2dint(duration_string)

    def is_ok(self):
        """Returns true is video file exist and it is actually a video.
        
        """
        return self.__in_ok
    

    def __find_ext_subtitle(self):
        if self.__in_ok:
            subtitle_filename_root=os.path.splitext(self.__in_filename)[0]
            for subtitle_extension in self.__sub_exts:
                subtitle_filename=subtitle_filename_root+subtitle_extension
                if os.path.isfile(subtitle_filename):
                    self.__ext_sub_files.append(subtitle_filename)
                    return

    def __try_to_convert_sub_to_srt(self):
        for sub_file in self.__sub_files:
            subtitle_filename_root,subtitle_filename_ext=os.path.splitext(sub_file)
            
            if subtitle_filename_ext == '.srt':
                continue
            
            srt_sub_file=ass2srt(sub_file)
            if srt_sub_file:
                self.__int_sub_files.append(srt_sub_file)   
                
    def set_transcoding_options(self,preset,crf,replace_original,avlang,slang,postfix,threads,auto_crop):
        if self.__in_ok:
            self.__preset = preset			
            self.__CRF = crf
            self.__find_ext_subtitle()
            self.__find_int_subtitles()

            self.__replace_original = replace_original            
            self.__default_avlang = avlang
            self.__default_slang = slang
##            self.__sub_exts.append(extra_sub_ext)
            self.__output_postfix = postfix
            self.__threads = threads
            if auto_crop:
                sys.stdout.write(_('Finding crop dimensions...'))
                sys.stdout.flush()
                self.__get_crop_data()
                
            self.__transcoding_options_set = True
            
    def __find_int_subtitles(self):
            n = 1
            in_filename_root,in_filename_ext=os.path.splitext(self.__in_filename)
            if in_filename_ext == '.mkv':
                for line in os.popen("mkvmerge -i \"{}\" -F verbose-text".format(self.__in_filename)):
                    if 'subtitles' in line:
                        track_id=int(line.strip().split(":")[0].split()[-1])
                        sub_type=line.strip().split('(')[1].split(")")[0]
                        slang = line[line.index("language:"):].split(':')[1].split()[0]
                        if slang:
                            if "unk" in slang.lower() or "und" in slang.lower():
                                    slang = None

                        sub_ext='.srt'
                        if sub_type in ['ASS','SSA', 'SubStationAlpha']:
                            sub_ext='.ass'
                            
                        #while(os.path.isfile(in_filename_root+"_"+str(n)+sub_ext)):
                        #    n+=1
                            
                        sub_filename = in_filename_root + "_tmp_" + random_string(10) + sub_ext
                            
                        os.system("mkvextract tracks \"{}\" {:d}:\"{}\"".format(self.__in_filename, track_id, sub_filename))
                        
                        self.__int_sub_files.append(sub_filename)
                        
                        if slang:
                            self.__slangs[sub_filename] = slang
                        
                        
    def transcode(self):
        if self.__transcoding_options_set:
            #cmd_line='ffmpeg -i \"{}\" -vcodec libx265 -crf {:d}'.format(self.__in_filename, self.__CRF)
            cmd_line='ffmpeg -i \"{}\" -c:v libx265 -preset {} -crf {:d}'.format(self.__in_filename, self.__preset, self.__CRF)
            if self.__crop_data:
                cmd_line+=' -vf crop={}'.format(self.__crop_data)
                
            #cmd_line+=' -acodec aac -ar 48k -ab 192k -strict experimental -sn -threads {:d} -y \"{}\"'.format(self.__threads, self.__ffmpeg_output)
            cmd_line+=' -c:a aac -ar 48k -b:a 192k -strict experimental -max_muxing_queue_size 9999 -sn -threads {:d} -y \"{}\"'.format(self.__threads, self.__ffmpeg_output)
            
            sys.stdout.write('> {}\n'.format(cmd_line))
            exit_code=os.system(cmd_line)
            
            if not exit_code:
                if not self.__create_complete_mkv():
                    return False
                
                if self.__replace_original:
                    sys.stderr.write(_("WARNING: Deleting file {} as commanded with -r option.\nThis file won't be easily recovered.\n").format(self.__in_filename))
                    os.remove(self.__in_filename)
                        
                return True

            #else:
            #    os.remove(self.__ffmpeg_output)
            #    self.__fmpeg_output = None
        
        return False
    
    def __create_complete_mkv(self):
        if self.__ffmpeg_output:
            ffmpeg_output_root=os.path.splitext(self.__ffmpeg_output)[0].replace(self.__ffmpeg_output_postfix,'')
            mkv_output=ffmpeg_output_root+self.__output_postfix+'.mkv'
            while os.path.isfile(mkv_output):
                mkv_output = mkv_output.replace(self.__output_postfix, '_' + self.__output_postfix)

            if not self.__avlang:
                self.__avlang = self.__default_avlang
                
            cmd_line="mkvmerge --default-language {} -o \"{}\" \"{}\"".format(self.__avlang,mkv_output,self.__ffmpeg_output)
            sub_files = self.__ext_sub_files + self.__int_sub_files
            if sub_files:
                for sub_file in sub_files:
                    if sub_file in self.__slangs:
                        slang = self.__slangs[sub_file]
                        
                    else:
                        slang = self.__default_slang
                        
                    cmd_line+="  --language 0:{}".format(slang)
                    self.__find_sub_charset(sub_file)
                    if self.__sub_charsets[sub_file]:
                        cmd_line+=" --sub-charset 0:{}".format(self.__sub_charsets[sub_file])
                        
                    cmd_line+=(" \"{}\" ".format(sub_file))
                
                
            sys.stdout.write('> {}\n'.format(cmd_line))
            exit_status=os.system(cmd_line)
            if not exit_status:
                #os.remove(self.__ffmpeg_output)
                #self.__ffmpeg_output=None
                return True        
        
        return False
    
    def __find_sub_charset(self, filename):
        cmd_output=os.popen("file -bi \"{}\" | sed -e 's/.*charset=//'".format(filename))
        for line in cmd_output:
            line=line.strip()
            if line:
                self.__sub_charsets[filename]=line
        
    def __get_crop_data(self):
        crop_data=None
        crop_list=[]
        tmp_output_filename=os.path.splitext(self.__in_filename)[0] + '_tmp_' + random_string(10)  +'_autocrop.mkv'
        input_duration=self.__in_duration
        if input_duration:
            ss_list=[input_duration/x for x in random.sample(range(1,100),5)] # Cheacking autocrop in 5 random sites in the video.
            for ss in ss_list:
                cproc = subprocess.run(["ffmpeg", "-ss", str(ss), "-i", self.__in_filename, "-t", "1", "-filter", "cropdetect", "-y", tmp_output_filename], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, universal_newlines=True)
                for line in cproc.stderr.split('\n'):
                    line=line.strip()
                    if ('cropdetect' in line) and ('=' in line):
                        crop_list.append(line.split('=')[1])
                        
            os.remove(tmp_output_filename)            
            crop_set=set(crop_list)
            crop_mode_cont=0
            for crop in crop_set:
                if crop_list.count(crop) > crop_mode_cont:
                    crop_data=crop
                    crop_mode_cont=crop_list.count(crop)
            
        sys.stdout.write('{}\n'.format(crop_data))
        self.__crop_data=crop_data
        
    def __purge_int_sub_files(self):
        if self.__int_sub_files:
            for sub_file in self.__int_sub_files:
                print(_("Removing temporary file '{}'.").format(sub_file))
                os.remove(sub_file)
                
    def clean(self):
        print(_("Removing temporary file '{}'.").format(self.__ffmpeg_output))
        os.remove(self.__ffmpeg_output)
        self.__ffmpeg_output = None
        self.__purge_int_sub_files()
    
class Reporter:
    """Holds information about the transcoding process and elaborate a final report.
    
    """
    def __init__(self):
        self.__files_ok_counter=0
        self.__files_with_error=[]
        self.__ignored_files=[]
        
    def count_file_ok(self):
        self.__files_ok_counter+=1
        
    def add_file_with_errors(self,filename):
        self.__files_with_error.append(filename)
        
    def add_ignored_file(self,filename):
        self.__ignored_files.append(filename)
        
    def print_final_report(self):
        """Print report after all transcoding is made.
        """
        print(_('\n==== Transcoding finished ===='))
        if self.__ignored_files:
            print (_('== There following files were ignored: =='))
            for filename in self.__ignored_files:
                print('\t* {}'.format(filename))
                
            print(75*'=')
            print('\n')
            
        if self.__files_with_error:
            print(_('== There were errors transcoding the files: =='))
            for filename in self.__files_with_error:
                print('\t* {}'.format(filename))
                
            print(75*'=')
            print('\n')
            
        print(_('==== Final report ===='))
        output = '\t {}'.format(self.__files_ok_counter)
        if self.__files_ok_counter == 1:
            output += _(' file')

        else:
            output += _(' files')
            
        output += _(' transcoded OK.\n')
        output += '\t {:d}'.format(len(self.__files_with_error))
                    
        if len(self.__files_with_error) == 1:
            output += _(' file')

        else:
            output += _(' files')
            
        output+=_(' with errors.\n')
        
        sys.stdout.write(output)
            
        print(75*'=')
        print('\n')

## Functions
def check_the_required_programs():
    if os.system("ffmpeg -h > /dev/null 2>&1"):
        sys.stderr.write(_("ERROR: ffmpeg is not installed in your system.\nThis script can not work properly without it.\n\n"))
        exit()
        
    if os.system("mkvmerge -h > /dev/null"):
        sys.stderr.write(_("ERROR: mkvtoolnix is not installed in your system.\nThis script can not work properly without it.\n\n"))
        exit()
        
def print_duration(seconds):
    output=''
    seconds_per_minute=60
    seconds_per_hour=60*seconds_per_minute
    seconds_per_day=24*seconds_per_hour
    
    days=int(seconds/seconds_per_day)
    hours=int((seconds % seconds_per_day)/seconds_per_hour)
    minutes=int((seconds % seconds_per_hour)/seconds_per_minute)
    seconds=seconds%60
    
    if days:
        #output+=('%d' % (days))
        output+=('{:d}'.format(days))
        if days==1:
            output+=_(' day ')
            
        else:
            output+=_(' days ')
            
    if hours:
        #output+=('%2d' % (hours))
        output+=('{:2d}'.format(hours))
        if hours==1:
            output+=_(' hour ')
            
        else:
            output+=_(' hours ')
            
    if minutes:
        #output+=('%2d' % (minutes))
        output+=('{:2d}'.format(minutes))
        if minutes==1:
            output+=_(' minute ')
            
        else:
            output+=_(' minutes ')
            
    if seconds:
        #output+=('%4.2f' % (seconds))
        output+=('{:4.2f}'.format(seconds))
        if seconds==1:
            output+=_(' second ')
            
        else:
            output+=_(' seconds ')
                
    return output.strip()

    
def ass2srt(in_filename):
    out_filename=os.path.splitext(in_filename)[0]+'.srt'
    in_file=open(in_filename,'r')
    out_file=open(out_filename,'w')
    dialog_counter=0
    for line in in_file:
        dialog=''
        line=line.strip()
        if line[:9] == 'Dialogue:':
            dialog_counter+=1
            fields=line[10:].split(',')
            ftime=line[10:].split(',')[1]
            ltime=line[10:].split(',')[2]
            for sentence in fields[3:]:
                dialog+=(sentence+',')
                
            dialog=dialog.rstrip(',')
            ftime_hour,ftime_min,ftime_seconds=ftime.split(':')
            ftime_hour,ftime_min=int(ftime_hour),int(ftime_min)
            ftime_seconds,ftime_mseconds=ftime_seconds.split('.')
            ftime_seconds,ftime_mseconds=int(ftime_seconds),int(ftime_mseconds)*10

            ltime_hour,ltime_min,ltime_seconds=ltime.split(':')
            ltime_hour,ltime_min=int(ltime_hour),int(ltime_min)
            ltime_seconds,ltime_mseconds=ltime_seconds.split('.')
            ltime_seconds,ltime_mseconds=int(ltime_seconds),int(ltime_mseconds)*10
            
            output_line="{:d}\n{:02d}:{:02d}:{:02d},{:03d} --> {:02d}:{:02d}:{:02d},{:03d}\n{}\n\n".format(dialog_counter,ftime_hour,ftime_min,ftime_seconds,ftime_mseconds,ltime_hour,ltime_min,ltime_seconds,ltime_mseconds,dialog)
            out_file.write(output_line)
            
    
    in_file.close()
    out_file.close()
    
    return out_filename

def dstring2dint(duration_string):
    hours,minutes,seconds=duration_string.split(':')
    hours,minutes,seconds=int(hours),int(minutes),int(round(float(seconds)))
    duration_seconds=3600*hours+60*minutes+seconds
    return duration_seconds

def random_string(length = 10):
    rand_string = ''
    for letter in random.sample(string.ascii_lowercase + string.ascii_uppercase + string.digits, length):
        rand_string += letter

    return rand_string

def run_script():
    """Function to be called to actually run the script.
    """
    check_the_required_programs()
    initial_time=time.time()
    parser=argparse.ArgumentParser(description=_("This program transcode video files to H265 and AAC in MKV format. Subtitles, if present, are automatically detected and soft subbed into the corresponding output files."), add_help=False)
    parser.add_argument('video', nargs='+', help=_('Input video file(s).'))
    parser.add_argument('-h','--help', action='help', help=_("Show this help message and exit."))
    parser.add_argument('-p', '--preset', default='medium', help=_('X265 preset [default: %(default)s].'))
    parser.add_argument('-q','--crf', type=int, default=28, help=_('CRF value [default: %(default)s]. Determines the output video quality. Smaller values gives better qualities and bigger file sizes, bigger values result in less quality and smaller file sizes. Default value results in a nice quality/size ratio. CRF values should be in the range of 1 to 50.'))
    parser.add_argument('-r', '--replace-original-video-file', action='store_true', default=False, dest='replace', help=_('If set then original video files will be erased after transcoding. WARNING: deleted files can not be easily recovered!'))
    parser.add_argument('-l','--avlang', default='eng', help=_('Default audio language for MKV files obtained (used only if the original stream languages fail to be determined) [default: %(default)s].'))
    parser.add_argument('-L', '--slang', default='spa', help=_('Default subtitle language of soft-subbed subtitles (only used if original subtitle languages fail to be determined) [default: %(default)s].'))
    parser.add_argument('-x', '--filename-postfix', default='_h265', help=_('Postfix to be added to newly created H.265 video files [default: %(default)s].'))
    parser.add_argument('-t', '--threads', type=int, default=0, help=_('Indicates the number of processor cores the script will use. 0 indicates to use as many as possible [default: %(default)s].'))
    parser.add_argument('-c', '--auto-crop', action='store_true', default=False, help=_('Turn on autocrop function. WARNING: Use with caution as some video files has variable width horizontal (and vertical) black bars, in those cases you will probably lose data.')) 
    parser.add_argument('-v', '--version', action='version', version='3.2.7', help=_("Show program's version number and exit.")) # I need to use this explicit help message here (together with setting add_help=False when creating the parser) to be able to proper translate the version help message (when required). All other messages are translated OK, but not this one. With this edit now everything is OK.
    
    args=parser.parse_args()

    if args.crf < 1 or args.crf > 50:
        parser.error(_('CRF values should be in the range of 1 to 50.'))
        
    if args.threads < 0:
        parser.error(_('The number of threads must be 0 or positive.'))

    known_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
    if args.preset not in known_presets:
        parser.error(_('Unknown preset "{}".\nValid values are:\n\t{}\n').format(args.preset, '\n\t'.join(known_presets)))

    reporter=Reporter()
    file_counter=0
    for filename in args.video:
        file_counter+=1        
        print(_('\n==== Transcoding file {:d}/{:d} ====').format(file_counter,len(args.video)))
        video=Video(filename)
        if not video.is_ok():
            sys.stderr.write(_("File {} is not a proper video file.\n").format(filename))
            reporter.add_ignored_file(filename)
            continue
        
        video.set_transcoding_options(args.preset, args.crf, args.replace, args.avlang, args.slang, args.filename_postfix, args.threads, args.auto_crop)
        if video.transcode():
            reporter.count_file_ok()
            #video.clean()
            
        else:
            reporter.add_file_with_errors(filename)

        video.clean() # Always clean, not only in success, please...
            
        print(75*'=')
            
    reporter.print_final_report()
        
    final_time=time.time()
    
    print(_('Work finished in {}.').format(print_duration(final_time-initial_time)))
    print(_('Exiting OK.'))
    
## Running the script
if __name__ == "__main__":
    run_script()
