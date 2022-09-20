import os
import json
from collections import OrderedDict

from hyperpyyaml import load_hyperpyyaml, dump_hyperpyyaml



def read_jsonl_file(fname):
    with open(fname, "r") as f:
        return [json.loads(line) for line in f]


def write_jsonl_file(fname, lines):
    with open(fname, "w") as fw:
        for line in f:
            fw.write(json.dumps(line, sort_keys=True)+"\n")


def load_hparams(hparams_fname, overrides=None):
    with open(hparams_fname, "r") as f:
        return load_hyperpyyaml(f, overrides=overrides)


def combine_multiple_hyperpyyaml_files_into_one(input_hyperpyyaml_files=None, extra_kv={}, output_hyperpyyaml_file=None):
    """
    # input_hyperpyyaml_files: dictionary of hyperpyyaml config files for this experiment
    # output_hyperpyyaml_file: str
    """
    combined_hparams = {}
    for k,v in input_hyperpyyaml_files.items():
        with open(v, "r") as f:
            combined_hparams[k] = load_hyperpyyaml(f)

    for k,v in extra_kv.items():
        combined_hparams[k] = v

    write_hyperpyyaml_file(output_hyperpyyaml_file, combined_hparams)


def write_hyperpyyaml_file(out_fname, hparams):    
    print(hparams)
    with open(out_fname, "w") as fw:
        dump_hyperpyyaml(hparams, fw)


def get_utterance_manifest_from_datasets(datasets):
    """
    INPUT:
        datasets: the datasets field from a data_config hyperpyyaml file

    OUTPUT:
        list of entries from .jsonl files. [{"audo_wav_file": ..., "transcript_all_file": ..., "filter_criteria": ...}, ...]
    """
    ### Convert to utterance manifest
    # at this stage, the trancsript info for each utterance is a filename with multiple trancsripts ('transcript_all_file')
    # and an uid into that file, `transcript_uid`
    corpus = []
    ignored_filter_criterias = set()
    for ds in datasets:
        filter_criterias_counts = OrderedDict([(k, 0) for k in ds["filter_criterias"]])
        entries = []
        for entry in read_jsonl_file(ds["map_file"]):
            if entry["filter_criteria"] in ds["filter_criterias"]:
                entries.append(entry)
            else:
                ignored_filter_criterias.update([entry["filter_criteria"]])

        # convert_to_absolute_paths:
        root_dir = os.path.dirname(ds["map_file"])
        for entry in entries:
            filter_criterias_counts[entry["filter_criteria"]] += 1
            entry["transcript_all_file"] = os.path.join(root_dir, entry["transcript_all_file"])
            entry["audio_wav_file"]      = os.path.join(root_dir, entry["audio_wav_file"])
            corpus.append(entry)

        ### Print Filter Criterias counts
        for k,v in filter_criterias_counts.items():
            print(f"{k}: {v}")
        #exit()
    print(filter_criterias_counts)
    print(f"ignored_filter_criterias: {ignored_filter_criterias}")
    print()

    ### Get list of transcript_all files and assert that they exist
    # beginning the effort to directly have the trnascripts in each entry instead of transcript_files and uids
    unique_transcript_all_files = list(set([entry["transcript_all_file"] for entry in corpus]))
    for x in unique_transcript_all_files:
        assert os.path.exists(x), "data transcript file {} does not exist! Exiting!".format(x)

    ### Get Transcript Map
    # key = transcript uid
    # value = transcript line
    # <s> અંબાલાલ ભાઈને ચાર વાર ભલામણ કરી છે ત્રિભોવનભાઇ ને બે વાર ભલામણ કરી છે </s> (b0d740f0-speaker1-00f44130)
    transcript_map = {}
    for transcript_all_file in unique_transcript_all_files:
        with open(transcript_all_file, "r") as f:
            for line in f:
                key = line.split("</s>")[-1].strip()[1:-1]

                line = line.strip().split()
                assert line[0]=="<s>"
                assert line[-2]=="</s>"
                transcript = " ".join(line[1:-2])

                transcript_map[key] = transcript

    for entry in corpus:
        assert entry["transcript_uid"] in transcript_map
        entry["transcript"] = transcript_map[entry["transcript_uid"]]
    
    return corpus
