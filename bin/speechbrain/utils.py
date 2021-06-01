import os
import json
from hyperpyyaml import load_hyperpyyaml



def read_jsonl_file(fname):
    with open(fname, "r") as f:
        return [json.loads(line) for line in f]


def write_jsonl_file(fname, lines):
    with open(fname, "w") as fw:
        for line in f:
            fw.write(json.dumps(line, sort_keys=True)+"\n")


def get_utterance_manifest_from_data_config(data_config):
    """
    INPUT:
        data_config in hyperpyyaml format

    OUTPUT:
        list of entries from .jsonl files. [{"audo_sph_file": ..., "transcript_file": ..., "filter_criteria": ...}, ...]
    """
    # Datasets
    with open(data_config, "r") as f:
        datasets = load_hyperpyyaml(f)["datasets"]

    # Convert to utterance manifest
    corpus = []
    for ds in datasets:
        entries = [entry for entry in read_jsonl_file(ds["map_file"]) if entry["filter_criteria"] in ds["filter_criterias"]]

        # convert_to_absolute_paths:
        root_dir = os.path.dirname(ds["map_file"])
        for entry in entries:
            entry["transcript_all_file"] = os.path.join(root_dir, entry["transcript_all_file"])
            corpus.append(entry)

    return corpus

