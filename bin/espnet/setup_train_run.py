import os
import glob
from constants import DATA_DIR, ESPNET_DIR



def empty_dir(dname):
    if DATA_DIR in dname:
        raise ValueError("trying to delete a data folder")
    cmd = "rm -rf {}".format(dname)
    os.system(cmd)


def copy_from_dir_to_dir(source_dir, dest_dir):
    os.system("mkdir -p {}".format(dest_dir))
    for fname in glob.glob(os.path.join(source_dir, "*")):
        cmd = "cp '{}' '{}'".format(fname, os.path.join(dest_dir, os.path.basename(fname)))
        os.system(cmd)


def copy_from_dir_to_file(source_dir, dest_file):
    os.system("mkdir -p {}".format(os.path.dirname(dest_file)))
    with open(dest_file, "a") as fw:
        for fname in glob.glob(os.path.join(source_dir, "*")):
            with open(fname, "r") as f:
                for line in f:
                    fw.write(line)


if __name__=="__main__":
    ##### ARGUMENTS #####
    DATA_DIR = os.path.join(DATA_DIR, "paryushan-2019")
    train_audio_dirs      = [os.path.join(DATA_DIR, "segmented-audio-sph/Day 1 - Pravachan 1 - 26th August 2019")]
    train_transcript_dirs = [os.path.join(DATA_DIR, "segmented-transcripts/Day 1 - Pravachan 1 - 26th August 2019")]

    test_audio_dirs      = [os.path.join(DATA_DIR, "segmented-audio-sph/Day 1 - Pravachan 1 - 26th August 2019")]
    test_transcript_dirs = [os.path.join(DATA_DIR, "segmented-transcripts/Day 1 - Pravachan 1 - 26th August 2019")]

    ##### RUN #####
    DEST_DIR = os.path.join(ESPNET_DIR, "egs/Bapa/asr1/downloads/Bapa")
    empty_dir(DEST_DIR)

    ### TRAIN
    for dname in train_audio_dirs:
        copy_from_dir_to_dir(dname, os.path.join(DEST_DIR, "wav", "train", "speaker1"))
    for dname in train_transcript_dirs:
        copy_from_dir_to_file(dname, os.path.join(DEST_DIR, "etc", "train.transcription"))

    ### TEST
    for dname in test_audio_dirs:
        copy_from_dir_to_dir(dname, os.path.join(DEST_DIR, "wav", "test", "speaker1"))
    for dname in test_transcript_dirs:
        copy_from_dir_to_file(dname, os.path.join(DEST_DIR, "etc", "test.transcription"))
    
