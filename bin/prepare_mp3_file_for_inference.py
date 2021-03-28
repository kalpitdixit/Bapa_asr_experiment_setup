import os
import sys
import glob
import sox



def convert_to_wav_file(mp3_fname, wav_fname):
    cmd = "ffmpeg -i {} -ar 48000 {}".format(mp3_fname, wav_fname)
    os.system(cmd)

    
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



if __name__=="__main__":
    """
    USAGE: python prepare_mp3_file_for_inference.py /path/to/mp3/file 
    """
    ##### ARGS #####
    mp3_fname = sys.argv[1]
    assert mp3_fname[-4:]==".mp3"    

    wav_fname = mp3_fname[:-4]+".wav"
    segments_dname = "tmp_segments"

    os.system("rm -rf {}".format(segments_dname))
    os.system("mkdir -p {}".format(segments_dname))

    ##### SEGMENT #####
    convert_to_wav_file(mp3_fname, wav_fname)
    segment_wav(wav_fname, segments_dname)
    convert_wav_segments_to_mp3(segments_dname)
        
    ##### CONVERT SEGMENTS: MP3 TO SPH #####
    convert_mp3_to_sph(segments_dname)
