import os
import glob
from constants import DATA_DIR, ESPNET_DIR
import argparse



def empty_dir(dname):
    if DATA_DIR in dname:
        raise ValueError("trying to delete a data folder")
    cmd = "rm -rf {}".format(dname)
    os.system(cmd)


def copy_from_dir_to_dir(source_dir, dest_dir, config, file_list_fname=None):
    os.system("mkdir -p {}".format(dest_dir))
    if file_list_fname is not None:
        os.system("mkdir -p {}".format(os.path.dirname(file_list_fname)))
        fw = open(file_list_fname, "a")  
    count = 0
    for fname in sorted(glob.glob(os.path.join(source_dir, "*"))):
        cmd = "cp '{}' '{}'".format(fname, os.path.join(dest_dir, os.path.basename(fname)))
        os.system(cmd)
    
        if file_list_fname is not None:
            fw.write("{} {} -f wav -p -c 1 {} |\n".format(os.path.basename(fname).replace(".sph", ""),
                                                          os.path.join(ESPNET_DIR, "tools/kaldi/tools/sph2pipe_v2.5/sph2pipe"),
                                                          os.path.join("downloads/Bapa/wav/an4{}_clstk/speaker1".format("test" if "an4test" in dest_dir else ""), os.path.basename(fname))))
        count += 1
        if config.tiny_train and count>=8:
            break

    if file_list_fname is not None:
        fw.close()


def copy_from_dir_to_file(source_dir, dest_file, allowed_ids, create_text_file=False):
    os.system("mkdir -p {}".format(os.path.dirname(dest_file)))

    with open(dest_file, "a") as fw:
        for fname in sorted(glob.glob(os.path.join(source_dir, "*"))):
            with open(fname, "r") as f:
                for line in f:
                    if allowed_ids is not None:
                        line_id = line.strip().split()[-1][1:-1]
                        if not line_id in allowed_ids:
                            continue
                    if create_text_file:
                        line = line.strip().split()
                        line = "{} {}\n".format(line[-1][1:-1], " ".join(line[1:-2]))
                    fw.write(line)
                        

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiny_train", action="store_true")
    return parser.parse_args()


if __name__=="__main__":
    ##### ARGUMENTS #####
    config = parser()
    #if config.tiny_train:
    #    raise NotImplementedError("not correctly implemented")

    ##### DATASETS #####
    train_audio_dirs = []
    train_transcript_dirs = []

    test_audio_dirs = []
    test_transcript_dirs = []

    ### TRAIN 1 ###
    DATA_DIR_this = os.path.join(DATA_DIR, "paryushan-2019")
    train_dirs = ["Day 1 - Pravachan 1 - 26th August 2019",
                  #"Day 2 - Pravachan 2 - 27th August 2019", # marked as test
                  "Day 3 - Pravachan 3 - 28th August 2019",
                  "Day 4 - Pravachan 4 - 29th August 2019",
                  "Day 6 - Pravachan 5 - 31st August 2019",
                  "Day 7 - Pravachan 6 - 1st September 2019"]
    for tdir in train_dirs:
        train_audio_dirs.append(os.path.join(DATA_DIR_this, "segmented-audio-sph/{}".format(tdir)))
        train_transcript_dirs.append(os.path.join(DATA_DIR_this, "segmented-transcripts/{}".format(tdir)))

    ### TEST 1 ###
    test_audio_dirs.append(os.path.join(DATA_DIR_this, "segmented-audio-sph/Day 2 - Pravachan 2 - 27th August 2019"))
    test_transcript_dirs.append(os.path.join(DATA_DIR_this, "segmented-transcripts/Day 2 - Pravachan 2 - 27th August 2019"))

    ### TRAIN 2 ###
    DATA_DIR_this = os.path.join(DATA_DIR, "2019-shri-yogvasishtha-maharamayan")
    train_dirs = ["Shibir 7 Paryushan Mahaparva/Pravachan 1",
                  #"Shibir 7 Paryushan Mahaparva/Pravachan 2", # marked as test
                  "Shibir 7 Paryushan Mahaparva/Pravachan 3",
                  "Shibir 7 Paryushan Mahaparva/Pravachan 4",
                  "Shibir 7 Paryushan Mahaparva/Pravachan 5",
                  "Shibir 7 Paryushan Mahaparva/Pravachan 6"]
    for tdir in train_dirs:
        tdir_with_Sewak = os.path.join(os.path.dirname(tdir)+" Sewak", os.path.basename(tdir))
        train_audio_dirs.append(os.path.join(DATA_DIR_this, "segmented-audio-sph/{}".format(tdir)))
        train_transcript_dirs.append(os.path.join(DATA_DIR_this, "segmented-transcripts/Part by part/{}".format(tdir_with_Sewak)))
    print(train_transcript_dirs)
    
    ##### RUN #####
    DEST_DIR = os.path.join(ESPNET_DIR, "egs/Bapa/asr1")
    empty_dir(os.path.join(DEST_DIR, "downloads"))
    empty_dir(os.path.join(DEST_DIR, "data"))
    os.system("rm -rf {}".format(os.path.join(DEST_DIR, "data", "train", "wav.scp")))
    os.system("rm -rf {}".format(os.path.join(DEST_DIR, "data", "test", "wav.scp")))

    ### TRAIN
    for dname in train_audio_dirs:
        copy_from_dir_to_dir(dname, os.path.join(DEST_DIR, "downloads", "Bapa", "wav", "an4_clstk", "speaker1"), config, 
                             file_list_fname=os.path.join(DEST_DIR, "data", "train", "wav.scp"))
        print(dname)

    allowed_ids = None
    if config.tiny_train:
        fname = os.path.join(DEST_DIR, "data", "train", "wav.scp")
        with open(fname, "r") as f:
            allowed_ids = [line.strip().split()[0] for line in f]

    for dname in train_transcript_dirs:
        copy_from_dir_to_file(dname, os.path.join(DEST_DIR, "data", "train", "text"), allowed_ids, create_text_file=True)
        copy_from_dir_to_file(dname, os.path.join(DEST_DIR, "downloads", "Bapa", "etc", "train.transcription"), allowed_ids)
        print(dname)
        print(os.path.join(DEST_DIR, "data", "train", "text"))


    ### TEST
    for dname in test_audio_dirs:
        copy_from_dir_to_dir(dname, os.path.join(DEST_DIR, "downloads", "Bapa", "wav", "an4test_clstk", "speaker1"), config,
                             file_list_fname=os.path.join(DEST_DIR, "data", "test", "wav.scp"))

    allowed_ids = None
    if config.tiny_train:
        fname = os.path.join(DEST_DIR, "data", "test", "wav.scp")
        with open(fname, "r") as f:
            allowed_ids = [line.strip().split()[0] for line in f]

    for dname in test_transcript_dirs:
        copy_from_dir_to_file(dname, os.path.join(DEST_DIR, "data", "test", "text"), allowed_ids, create_text_file=True)
        copy_from_dir_to_file(dname, os.path.join(DEST_DIR, "downloads", "Bapa", "etc", "test.transcription"), allowed_ids)


    ### add README
    with open(os.path.join(DEST_DIR, "downloads", "Bapa", "README"), "w") as f:
        f.write("tmp\n")

