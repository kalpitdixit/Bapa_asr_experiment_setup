import os
import json
import hashlib
import re

from constants import DATA_DIR

time_pattern = re.compile("\d\d:\d\d:\d\d", re.ASCII)



def get_hash(s):
    h = hashlib.sha1()
    h.update(s.encode("utf-8"))
    return h.hexdigest()


def convert_to_seconds(s):
    assert len(s)==8, "expected len(s) to be 8, but got len {}: {}".format(len(s), s)
    assert time_pattern.match(s)
    return float(s[0:2])*3600 + float(s[3:5])*60 + float(s[6:8])


def empty_dir(dname, allow_data_folder_deletion=False):
    if not allow_data_folder_deletion:
        if DATA_DIR in dname:
            raise ValueError("trying to delete a data folder")
    cmd = "rm -rf '{}'".format(dname)
    os.system(cmd)


def read_jsonl_file(fname):
    with open(fname, "r") as f:
        return [json.loads(line) for line in f]


def write_jsonl_file(fname, lines):
    with open(fname, "w") as fw:
        for line in lines:
            fw.write(json.dumps(line, sort_keys=True)+"\n")


