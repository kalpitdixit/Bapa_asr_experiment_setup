import os
import glob
from constants import DATA_DIR, ESPNET_DIR
import argparse
from utils import read_jsonl_file


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


def copy_files_to_dir(source_fnames, dest_dir, config, file_list_fname=None):
    os.system("mkdir -p {}".format(dest_dir))
    if file_list_fname is not None:
        os.system("mkdir -p {}".format(os.path.dirname(file_list_fname)))
        fw = open(file_list_fname, "a")  
    count = 0
    for fname in source_fnames:
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


def copy_transcript_uids_to_file(corpus, dest_file, allowed_ids, create_text_file=False):
    """
    INPUT:
    corpus: list of entries from .jsonl files. [{"audo_sph_file": ..., "transcript_all_file": ..., "transcript_uid": ..., "filter_criteria": ...}, ...]
    """

    assert len(set([entry["transcript_all_file"] for entry in corpus]))==1

    ### Get Transcript Map
    # key = transcript uid
    # value = transcript line
    # <s> અંબાલાલ ભાઈને ચાર વાર ભલામણ કરી છે ત્રિભોવનભાઇ ને બે વાર ભલામણ કરી છે </s> (b0d740f0-speaker1-00f44130)
    transcript_map = {}
    with open(corpus[0]["transcript_all_file"], "r") as f:
        for line in f:
            key = line.split("</s>")[-1].strip()[1:-1]
            transcript_map[key] = line

    os.system("mkdir -p {}".format(os.path.dirname(dest_file)))

    with open(dest_file, "a") as fw:
        for entry in corpus:
            assert entry["transcript_uid"] in transcript_map
            line = transcript_map[entry["transcript_uid"]]
            if create_text_file:
                line = line.strip().split()
                line = "{} {}\n".format(line[-1][1:-1], " ".join(line[1:-2]))
            fw.write(line)
    

def get_corpus_from_sets(sets, convert_to_absolute_paths=True):
    """ 
    OUTPUT:
        list of entries from .jsonl files. [{"audo_sph_file": ..., "transcript_file": ..., "filter_criteria": ...}, ...]
    """
    corpus = []
    for s in sets:
        filter_criterias = s["filter_criterias"]
        
        entries = [entry for entry in read_jsonl_file(s["map_file"]) if entry["filter_criteria"] in filter_criterias]

        if convert_to_absolute_paths:
            root_dir = os.path.dirname(s["map_file"])
            for entry in entries:
                entry["audio_sph_file"]      = os.path.join(root_dir, entry["audio_sph_file"])
                entry["transcript_all_file"] = os.path.join(root_dir, entry["transcript_all_file"])
                corpus.append(entry)
        else:
            corpus.extend(entries)
    
    return corpus
                        

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiny_train", action="store_true")
    return parser.parse_args()



if __name__=="__main__":
    ##### ARGUMENTS #####
    config = parser()
    if config.tiny_train:
        raise NotImplementedError

    ##### DATASETS #####
    train_sets = [{"map_file": "/home/ubuntu/data/2019-shri-yogvasishtha-maharamayan/segmented_audios_sph_transcripts_map.json",
                   "filter_criterias": ["Shibir 1,Pravachan 1", "Shibir 1,Pravachan 3", "Shibir 1,Pravachan 4", "Shibir 1,Pravachan 5"]}]

    #train_sets = [{"map_file": "/home/ubuntu/data/2019-shri-yogvasishtha-maharamayan/segmented_audios_sph_transcripts_map.json",
    #               "filter_criterias": ['Shibir 1,Pravachan 1', 'Shibir 1,Pravachan 3', 'Shibir 1,Pravachan 4', 'Shibir 1,Pravachan 5',
    #                                    'Shibir 2,Pravachan 1', 'Shibir 2,Pravachan 2', 'Shibir 2,Pravachan 3']}]

    #train_sets = [{"map_file": "/home/ubuntu/data/2019-shri-yogvasishtha-maharamayan/segmented_audios_sph_transcripts_map.json",
    #               "filter_criterias": ['Shibir 1,Pravachan 1', 'Shibir 1,Pravachan 3', 'Shibir 1,Pravachan 4', 'Shibir 1,Pravachan 5', 'Shibir 10 Granth Poornahuti,Pravachan 1', 'Shibir 10 Granth Poornahuti,Pravachan 2', 'Shibir 10 Granth Poornahuti,Pravachan 3', 'Shibir 10 Granth Poornahuti,Pravachan 4', 'Shibir 2,Pravachan 1', 'Shibir 2,Pravachan 2', 'Shibir 2,Pravachan 3', 'Shibir 3,Pravachan 1', 'Shibir 3,Pravachan 2', 'Shibir 3,Pravachan 3', 'Shibir 4,Pravachan 1', 'Shibir 4,Pravachan 2', 'Shibir 4,Pravachan 3', 'Shibir 5,Pravachan 1', 'Shibir 5,Pravachan 2', 'Shibir 5,Pravachan 3', 'Shibir 5,Pravachan 4', 'Shibir 6,Pravachan 1', 'Shibir 6,Pravachan 2', 'Shibir 6,Pravachan 3', 'Shibir 6,Pravachan 4', 'Shibir 7 Paryushan Mahaparva,Pravachan 1', 'Shibir 7 Paryushan Mahaparva,Pravachan 2', 'Shibir 7 Paryushan Mahaparva,Pravachan 3', 'Shibir 7 Paryushan Mahaparva,Pravachan 4', 'Shibir 7 Paryushan Mahaparva,Pravachan 5', 'Shibir 7 Paryushan Mahaparva,Pravachan 6', 'Shibir 8,Pravachan 1', 'Shibir 8,Pravachan 2', 'Shibir 8,Pravachan 3', 'Shibir 9 Diwali,Pravachan 1', 'Shibir 9 Diwali,Pravachan 2', 'Shibir 9 Diwali,Pravachan 3', 'Shibir 9 Diwali,Pravachan 4', 'Shibir 9 Diwali,Pravachan 5', 'Shibir 9 Diwali,Pravachan 6', 'Shibir 9 Diwali,Pravachan 7']}]
    test_sets  = [{"map_file": "/home/ubuntu/data/2019-shri-yogvasishtha-maharamayan/segmented_audios_sph_transcripts_map.json",
                   "filter_criterias": ["Shibir 1,Pravachan 2"]}]
    
    train_corpus = get_corpus_from_sets(train_sets) # list of entries from .jsonl files. [{"audo_sph_file": ..., "transcript_all_file": ...,
                                                    #                                      "transcript_uid": ..., "filter_criteria": ...}, ...]
    test_corpus  = get_corpus_from_sets(test_sets)

    print("# Train Corpus entries: {:6,d}".format(len(train_corpus)))
    print("# Test  Corpus entries: {:6,d}".format(len(test_corpus)))
    print()

    """
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
    """
    

    ##### RUN #####
    ### SETUP EXPERIMENT DIRECTORY
    new_exp_num = get_new_exp_num(os.path.join(ESPNET_DIR, "egs/Bapa")) # /home/ubuntu/code/espnet/egs/Bapa

    TEMPLATE_EXP_DIR = "template_exp"
    DEST_DIR = os.path.join(ESPNET_DIR, "egs/Bapa/asr_exp_{}".format(new_exp_num))
    print("Destination Directory : {}".format(DEST_DIR))
    print()

    os.system("cp -r {} {}".format(TEMPLATE_EXP_DIR, DEST_DIR))

    empty_dir(os.path.join(DEST_DIR, "downloads"))
    empty_dir(os.path.join(DEST_DIR, "data"))
    os.system("rm -rf {}".format(os.path.join(DEST_DIR, "data", "train", "wav.scp")))
    os.system("rm -rf {}".format(os.path.join(DEST_DIR, "data", "test", "wav.scp")))

    ### TRAIN
    # Audio Files
    copy_files_to_dir([x["audio_sph_file"] for x in train_corpus],
                      os.path.join(DEST_DIR, "downloads", "Bapa", "wav", "an4_clstk", "speaker1"), config, 
                      file_list_fname=os.path.join(DEST_DIR, "data", "train", "wav.scp"))

    allowed_ids = None
    """
    if config.tiny_train:
        fname = os.path.join(DEST_DIR, "data", "train", "wav.scp")
        with open(fname, "r") as f:
            allowed_ids = [line.strip().split()[0] for line in f]
    """

    # Transcript Files
    copy_transcript_uids_to_file(train_corpus,
                                 os.path.join(DEST_DIR, "data", "train", "text"),
                                 allowed_ids,
                                 create_text_file=True)
    copy_transcript_uids_to_file(train_corpus,
                                 os.path.join(DEST_DIR, "downloads", "Bapa", "etc", "train.transcription"),
                                 allowed_ids)

    ### TEST
    # Audio Files
    copy_files_to_dir([x["audio_sph_file"] for x in test_corpus],
                      os.path.join(DEST_DIR, "downloads", "Bapa", "wav", "an4test_clstk", "speaker1"), config, 
                      file_list_fname=os.path.join(DEST_DIR, "data", "test", "wav.scp"))

    allowed_ids = None
    """
    if config.tiny_train:
        fname = os.path.join(DEST_DIR, "data", "test", "wav.scp")
        with open(fname, "r") as f:
            allowed_ids = [line.strip().split()[0] for line in f]
    """

    # Transcript Files
    copy_transcript_uids_to_file(test_corpus,
                                 os.path.join(DEST_DIR, "data", "test", "text"),
                                 allowed_ids,
                                 create_text_file=True)
    copy_transcript_uids_to_file(test_corpus,
                                 os.path.join(DEST_DIR, "downloads", "Bapa", "etc", "test.transcription"),
                                 allowed_ids)

    ### add README
    with open(os.path.join(DEST_DIR, "downloads", "Bapa", "README"), "w") as f:
        f.write("tmp\n")

