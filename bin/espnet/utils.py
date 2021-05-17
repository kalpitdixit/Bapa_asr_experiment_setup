import json


def read_jsonl_file(fname):
    with open(fname, "r") as f:
        return [json.loads(line) for line in f]
