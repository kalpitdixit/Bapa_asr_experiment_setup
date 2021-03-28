import os
import sys
import glob
from constants import DATA_DIR, ESPNET_DIR
import argparse
from utils import read_jsonl_file
import uuid


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


def copy_files_to_dir(source_fnames, dest_dir, file_list_fname=None):
    os.system("mkdir -p {}".format(dest_dir))

    if file_list_fname is not None:
        os.system("mkdir -p {}".format(os.path.dirname(file_list_fname)))
        fw = open(file_list_fname, "a")  

    for fname in source_fnames:
        cmd = "cp '{}' '{}'".format(fname, os.path.join(dest_dir, os.path.basename(fname)))
        os.system(cmd)
    
        if file_list_fname is not None:
                                                          
            if "an4test" in dest_dir:
                x = "downloads/Bapa/wav/an4{}_clstk/speaker1".format("test") 
            elif "an4inference" in dest_dir:
                x = "downloads/Bapa/wav/an4{}_clstk/speaker1".format("inference") 
            else:
                x = "downloads/Bapa/wav/an4{}_clstk/speaker1".format("") 
            fw.write("{} {} -f wav -p -c 1 {} |\n".format(os.path.basename(fname).replace(".sph", ""),
                                                          os.path.join(ESPNET_DIR, "tools/kaldi/tools/sph2pipe_v2.5/sph2pipe"),
                                                          os.path.join(x, os.path.basename(fname))))

    if file_list_fname is not None:
        fw.close()


def copy_transcript_uids_to_file(corpus, dest_file, allowed_ids, create_text_file=False):
    """
    INPUT:
    corpus: list of entries from .jsonl files. [{"audo_sph_file": ..., "transcript_all_file": ..., "transcript_uid": ..., "filter_criteria": ...}, ...]
    """

    #assert len(set([entry["transcript_all_file"] for entry in corpus]))==1, "exepcted 1 got {}".format(len(set([entry["transcript_all_file"] for entry in corpus])))
    unique_transcript_all_files = list(set([entry["transcript_all_file"] for entry in corpus]))
    
    if unique_transcript_all_files == [None]:
        print("No transcript files found!!!")

    ### Get Transcript Map
    # key = transcript uid
    # value = transcript line
    # <s> અંબાલાલ ભાઈને ચાર વાર ભલામણ કરી છે ત્રિભોવનભાઇ ને બે વાર ભલામણ કરી છે </s> (b0d740f0-speaker1-00f44130)
    transcript_map = {}
    if unique_transcript_all_files != [None]:
        for transcript_all_file in unique_transcript_all_files:
            with open(transcript_all_file, "r") as f:
                for line in f:
                    key = line.split("</s>")[-1].strip()[1:-1]
                    transcript_map[key] = line

    os.system("mkdir -p {}".format(os.path.dirname(dest_file)))
    os.system("rm -f {}".format(dest_file))

    print(dest_file)
    with open(dest_file, "a") as fw:
        for entry in corpus:
            if unique_transcript_all_files != [None]:
                assert entry["transcript_uid"] in transcript_map
                line = transcript_map[entry["transcript_uid"]]
                if create_text_file:
                    line = line.strip().split()
                    line = "{} {}\n".format(line[-1][1:-1], " ".join(line[1:-2]))
            else:
                line = "<s> dummy </s> ({})\n".format(entry["uid"])
                if create_text_file:
                    line = line.strip().split()
                    line = "{} {}\n".format(line[-1][1:-1], "")
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
                 
       
def get_corpus_from_sph_segments(sph_segments_dname):
    """ 
    OUTPUT:
        list of entries from .jsonl files. [{"audo_sph_file": ..., "transcript_file": ..., "filter_criteria": ...}, ...]
    """
    corpus = []
    for i,sph_segment in enumerate(sorted(list(glob.glob(os.path.join(sph_segments_dname, "*sph"))))):
        #utt_id = str(uuid.uuid4())[:8]
        entry =  {"audio_sph_file": sph_segment,
                  "transcript_file": None,
                  "filter_criteria": None,
                  "transcript_all_file": None,
                  "uid": os.path.basename(sph_segment).replace(".sph", "")}
        corpus.append(entry)
    return corpus



if __name__=="__main__":
    """
    USAGE: python setup_inference.py /home/ubuntu/code/espnet/egs/Bapa/asr1 tmp_segments
    """
    ##### ARGUMENTS #####
    DEST_DIR = sys.argv[1]
    sph_segments_dname = sys.argv[2]

    ##### DATASETS #####
    inference_corpus = get_corpus_from_sph_segments(sph_segments_dname)

    print("# Inference Corpus entries: {:6,d}".format(len(inference_corpus)))
    print()

    ##### RUN #####
    print("Destination Directory : {}".format(DEST_DIR))
    print()

    empty_dir(os.path.join(DEST_DIR, "data", "inference"))
    os.system("rm -rf {}".format(os.path.join(DEST_DIR, "data", "inference", "wav.scp")))
    empty_dir(os.path.join(DEST_DIR, "downloads/Bapa/wav/an4inference_clstk"))

    ### INFERENCE
    # Audio Files
    copy_files_to_dir([x["audio_sph_file"] for x in inference_corpus],
                      os.path.join(DEST_DIR, "downloads", "Bapa", "wav", "an4inference_clstk", "speaker1"), 
                      file_list_fname=os.path.join(DEST_DIR, "data", "inference", "wav.scp"))

    allowed_ids = None

    # Transcript Files
    copy_transcript_uids_to_file(inference_corpus,
                                 os.path.join(DEST_DIR, "data", "inference", "text"),
                                 allowed_ids,
                                 create_text_file=True)
    copy_transcript_uids_to_file(inference_corpus,
                                 os.path.join(DEST_DIR, "downloads", "Bapa", "etc", "inference.transcription"),
                                 allowed_ids)
