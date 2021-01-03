import os
import glob
from constants import DATA_DIR, ESPNET_DIR
import argparse



def get_new_exp_num(dname):
    fname = os.path.join(dname, "exp_num.txt")
    if not os.path.exists(fname):
        new_exp_num = 1
    else:
        with open(fname, "r") as f:
            new_exp_num = 1 + int(f.readline().strip())
    with open(fname, "w") as fw:
        fw.write(str(new_exp_num)+"\n")
    return new_exp_num

    
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

    DATA_DIR = os.path.join(DATA_DIR, "paryushan-2019")
    train_dirs = ["Day 1 - Pravachan 1 - 26th August 2019",
                  #"Day 2 - Pravachan 2 - 27th August 2019", # marked as text
                  "Day 3 - Pravachan 3 - 28th August 2019",
                  "Day 4 - Pravachan 4 - 29th August 2019",
                  "Day 6 - Pravachan 5 - 31st August 2019",
                  "Day 7 - Pravachan 6 - 1st September 2019"]
    train_audio_dirs = []
    train_transcript_dirs = []
    for tdir in train_dirs:
        train_audio_dirs.append(os.path.join(DATA_DIR, "segmented-audio-sph/{}".format(tdir)))
        train_transcript_dirs.append(os.path.join(DATA_DIR, "segmented-transcripts/{}".format(tdir)))

    test_audio_dirs      = [os.path.join(DATA_DIR, "segmented-audio-sph/Day 2 - Pravachan 2 - 27th August 2019")]
    test_transcript_dirs = [os.path.join(DATA_DIR, "segmented-transcripts/Day 2 - Pravachan 2 - 27th August 2019")]

    ##### RUN #####
    new_exp_num = get_new_exp_num(os.path.join(ESPNET_DIR, "egs/Bapa")) # /home/ubuntu/code/espnet/egs/Bapa

    TEMPLATE_EXP_DIR = "template_exp"
    #TEMPLATE_EXP_DIR = os.path.join(ESPNET_DIR, "egs/Bapa/template_exp")
    DEST_DIR = os.path.join(ESPNET_DIR, "egs/Bapa/asr_exp_{}".format(new_exp_num))
    #DEST_DIR = os.path.join(ESPNET_DIR, "egs/Bapa/asr1")
    print("Destination Directory : {}".format(DEST_DIR))

    os.system("cp -r {} {}".format(TEMPLATE_EXP_DIR, DEST_DIR))
    empty_dir(os.path.join(DEST_DIR, "downloads"))
    empty_dir(os.path.join(DEST_DIR, "data"))
    os.system("rm -rf {}".format(os.path.join(DEST_DIR, "data", "train", "wav.scp")))
    os.system("rm -rf {}".format(os.path.join(DEST_DIR, "data", "test", "wav.scp")))

    ### TRAIN
    for dname in train_audio_dirs:
        copy_from_dir_to_dir(dname, os.path.join(DEST_DIR, "downloads", "Bapa", "wav", "an4_clstk", "speaker1"), config, 
                             file_list_fname=os.path.join(DEST_DIR, "data", "train", "wav.scp"))

    allowed_ids = None
    if config.tiny_train:
        fname = os.path.join(DEST_DIR, "data", "train", "wav.scp")
        with open(fname, "r") as f:
            allowed_ids = [line.strip().split()[0] for line in f]

    for dname in train_transcript_dirs:
        copy_from_dir_to_file(dname, os.path.join(DEST_DIR, "data", "train", "text"), allowed_ids, create_text_file=True)
        copy_from_dir_to_file(dname, os.path.join(DEST_DIR, "downloads", "Bapa", "etc", "train.transcription"), allowed_ids)


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

