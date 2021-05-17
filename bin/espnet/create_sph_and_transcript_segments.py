import sys
import os
import glob
import docx
import re
import hashlib
import uuid
import json
from constants import DATA_DIR, KALDI_DIR


sph2pipe = os.path.join(KALDI_DIR, "tools/sph2pipe_v2.5/sph2pipe")
time_pattern = re.compile("\d\d:\d\d:\d\d", re.ASCII)
punctuations = [".", ",", "!", "?"]


def get_hash(s):
    h = hashlib.sha1()
    h.update(s.encode("utf-8"))
    return h.hexdigest()


def convert_to_seconds(s):
    assert len(s)==8, "expected len(s) to be 8, but got len {}: {}".format(len(s), s)
    assert time_pattern.match(s)
    return float(s[0:2])*3600 + float(s[3:5])*60 + float(s[6:8])


def empty_dir(dname):
    if DATA_DIR in dname:
        raise ValueError("trying to delete a data folder")
    cmd = "rm -rf '{}'".format(dname)
    os.system(cmd)


def get_transcript_segments(fname):
    transcript_segments = [] # list. each element is (start_time, end_time, text, uid). times are in seconds.
    pattern = re.compile("\d\d:\d\d:\d\d - \d\d:\d\d:\d\d", re.ASCII)

    doc = docx.Document(fname)
    for para in doc.paragraphs:
        text = para.text
        text = text.strip()
        if text=="":
            continue
        if not pattern.match(text[:19]):
            continue
        start_time = convert_to_seconds(text[:8])
        end_time   = convert_to_seconds(text[11:19])
        transcript = text[19:]
        for punct in punctuations:
            transcript = transcript.replace(punct, "")
        if transcript=="":
            continue
        transcript = transcript.strip()

        # see reason for not using global speaker ID by searching for "bold" in http://kaldi-asr.org/doc/data_prep.html
        utt_id = str(uuid.uuid4())[:8]
        uid = "{}-{}-{}".format(get_hash(transcript)[:8], "speaker1", str(uuid.uuid4())[:8])
        #uid = "{}-{}-{}".format(get_hash(transcript)[:8], utt_id, utt_id)

        if start_time >= end_time:
            continue

        transcript_segments.append((start_time, end_time, transcript, uid))
    return transcript_segments
    
        
def write_segmented_sphs_and_transcripts(data_dir, inp_sph_fname, transcript_segments, out_sph_dname, out_transcript_dname, entry):
    out_transcript_fname    = os.path.join(out_transcript_dname, "all.transcriptions")
    out_segmented_map_fname = os.path.join(data_dir, "segmented_audios_sph_transcripts_map.json")

    with open(out_transcript_fname, "a") as fw, open(out_segmented_map_fname, "a") as fw_map:
        for i,seg in enumerate(transcript_segments):
            stime, etime, transcript, uid = seg[:]

            ## SPH
            out_sph_fname = os.path.join(out_sph_dname, "{}.sph".format(uid))
            cmd = "{} -f sph -t {}:{} '{}' '{}'".format(sph2pipe, stime, etime, inp_sph_fname, out_sph_fname)
            os.system(cmd)

            ### Transcript
            out_str = "<s> {} </s> ({})".format(transcript, uid)
            fw.write(out_str+"\n")

            ## Segmented Map
            segmented_entry = {"audio_sph_file"     : os.path.relpath(out_sph_fname, data_dir),
                               "transcript_all_file": os.path.relpath(out_transcript_fname, data_dir),
                               "transcript_uid"     : uid,
                               "filter_criteria"    : entry["filter_criteria"]}
            fw_map.write(json.dumps(segmented_entry)+"\n")
            

def read_jsonl_file(fname):
    with open(fname, "r") as f:
        return [json.loads(line) for line in f]


def remove_first_dir(path):
    path_parts = [os.path.basename(path)]
    path = os.path.dirname(path)
    while path not in ["", "."]:
        path_parts.append(os.path.basename(path))
        path = os.path.dirname(path)
    path_parts = path_parts[::-1]
    return os.path.join(*path_parts[1:])
        
        

if __name__=="__main__":
    ##### ARGUMENTS #####
    audios_sph_to_transcript_fname = sys.argv[1]
    data_dir = os.path.dirname(audios_sph_to_transcript_fname)
    audios_sph_to_transcript_map = read_jsonl_file(audios_sph_to_transcript_fname)

    out_sph_dname        = os.path.join(data_dir, "segmented-audio-sph")
    out_transcript_dname = os.path.join(data_dir, "segmented-transcripts")

    for dname in [out_sph_dname, out_transcript_dname]:
        empty_dir(dname)
        if not os.path.exists(dname):
            os.makedirs(dname)

    for entry in audios_sph_to_transcript_map:
        inp_sph_fname        = os.path.join(data_dir, entry["audio_sph_file"])
        inp_transcript_fname = os.path.join(data_dir, entry["transcript_file"])
        filter_criteria      = entry["filter_criteria"]

        ##### RUN #####
        transcript_segments = get_transcript_segments(inp_transcript_fname) # list. each elem is (start_time, end_time, text). times are in seconds.
        write_segmented_sphs_and_transcripts(data_dir, inp_sph_fname, transcript_segments, out_sph_dname, out_transcript_dname, entry)
    
