import sys
import os
import json


def read_jsonl_file(fname):
    with open(fname, "r") as f:
        return [json.loads(line) for line in f]



if __name__=="__main__":
    """
    USAGE: python check_maaping_file /path/to/mapping/file
    """
    mapping_file = sys.argv[1]
    root_dir = os.path.dirname(mapping_file)

    maps = read_jsonl_file(mapping_file)

    for entry in maps:
        inp_sph_fname        = os.path.join(root_dir, entry["audio_sph_file"])
        inp_transcript_fname = os.path.join(root_dir, entry["transcript_file"])
        filter_criteria      = entry["filter_criteria"]

        assert os.path.exists(inp_sph_fname), "{} does not exist!".format(inp_sph_fname)
        assert os.path.exists(inp_transcript_fname), "{} does not exist!".format(inp_transcript_fname)

    # get all unique filter_criteria
    unique_filter_criteria = list(set([entry["filter_criteria"] for entry in maps]))
    print(unique_filter_criteria)
    print(len(unique_filter_criteria))
