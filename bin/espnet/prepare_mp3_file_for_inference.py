import os
import sys
import glob
import sox
import argparse
import uuid



def convert_to_wav_file(mp3_fname, wav_fname):
    cmd = "ffmpeg -i {} -ar 48000 {}".format(mp3_fname, wav_fname)
    os.system(cmd)

        
def segment_wav_using_existing_timestamps(mp3_fname, mp3_segment_dname, timestamps_txt_file):
    with open(timestamps_txt_file, "r") as f, open(os.path.join(mp3_segment_dname, "timestamps.txt"), "w") as fw:
        count = 0
        for line in f:
            line = line.strip()
            if line=="":
                continue
            line = line.split(" ")
            start_time = line[0]
            end_time   = line[2]

            utt_id = "{:08d}".format(count)
            seg_name = '{}-{}-{}'.format(utt_id, "speaker1", utt_id)
    
            cmd = "ffmpeg -i {} -ar 44100 -ss {} -to {} {}/{}.mp3".format(mp3_fname, start_time, end_time, mp3_segment_dname, seg_name)
            os.system(cmd)

            fw.write("{} {} {}\n".format(seg_name, start_time, end_time))
            count += 1
    
    
def segment_wav(wav_fname, wav_segment_dname):
    cmd = "python segment_wav.py 0 {} {}".format(wav_fname, wav_segment_dname)
    os.system(cmd)


def convert_wav_segments_to_mp3(wav_segment_dname):
    for wav_segment_fname in glob.glob(os.path.join(wav_segment_dname, "*wav")):
        cmd = "ffmpeg -i {} -ar 44100 {}".format(wav_segment_fname, wav_segment_fname[:-4:]+".mp3")
        os.system(cmd)
        cmd = "rm -f {}".format(wav_segment_fname)
        os.system(cmd)


def convert_mp3_to_sph(mp3_dname):
    # create transformer
    tfm = sox.Transformer()
    for mp3_fname in glob.glob(os.path.join(mp3_dname, "*mp3")):
        sph_fname = mp3_fname[:-4] + ".sph"
        tfm.build_file(mp3_fname, sph_fname)


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("mp3_fname", type=str)
    parser.add_argument("--timestamps_txt_file", type=str)
    return parser.parse_args()



if __name__=="__main__":
    """
    USAGE: python prepare_mp3_file_for_inference.py /path/to/mp3/file 
    """
    ##### ARGS #####
    args = arg_parser()
    assert args.mp3_fname[-4:]==".mp3"    

    wav_fname = args.mp3_fname[:-4]+".wav"
    segments_dname = "tmp_segments"
    os.system("rm -rf {}/*".format(segments_dname))

    os.system("rm -rf {}".format(segments_dname))
    os.system("mkdir -p {}".format(segments_dname))

    ##### SEGMENT #####
    if args.timestamps_txt_file:
        segment_wav_using_existing_timestamps(wav_fname, segments_dname, args.timestamps_txt_file)
    else:
        convert_to_wav_file(args.mp3_fname, wav_fname)
        segment_wav(wav_fname, segments_dname)
        convert_wav_segments_to_mp3(segments_dname)
        
    ##### CONVERT SEGMENTS: MP3 TO SPH #####
    convert_mp3_to_sph(segments_dname)
