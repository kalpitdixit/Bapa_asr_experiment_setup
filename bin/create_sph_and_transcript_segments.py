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

        transcript_segments.append((start_time, end_time, transcript, uid))
    return transcript_segments
    
    
def write_segmented_sphs(inp_sph_fname, transcript_segments, out_sph_dname):
    for i,seg in enumerate(transcript_segments):
        stime, etime, _, uid = seg[:]
            
        #out_sph_fname = os.path.basename(inp_sph_fname).split(".sph")[0] + "-seg-{}".format(i+1) + ".sph"
        #out_sph_fname = os.path.join(out_sph_dname, out_sph_fname)
        out_sph_fname = os.path.join(out_sph_dname, "{}.sph".format(uid))
        cmd = "{} -f sph -t {}:{} '{}' '{}'".format(sph2pipe, stime, etime, inp_sph_fname, out_sph_fname)
        os.system(cmd)
        #os.system("ls -l '{}' | wc -l".format(os.path.dirname(out_sph_fname)))


def write_segmented_transcripts(transcript_segments, out_transcript_dname):
    with open(os.path.join(out_transcript_dname, "all.transcriptions"), "a") as fw:
        for i,seg in enumerate(transcript_segments):
            _, _, transcript, uid = seg[:]
            out_str = "<s> {} </s> ({})".format(transcript, uid)
            fw.write(out_str+"\n")


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
    #inp_sph_fname        = sys.argv[1] # /home/ubuntu/data/paryushan-2019/audios-sph/Day 1 - Pravachan 1 - 26th August 2019
    #inp_transcripts_fname = sys.argv[2] # Pr1-Part 1-PTK522-PARYUSHAN2019-26082019-Atm. Sonalben-10092019.docx

    #inp_dname = "Day 2 - Pravachan 2 - 27th August 2019"
    #inp_dname = "Day 1 - Pravachan 1 - 26th August 2019"

    """
    inp_dnames = ["Day 1 - Pravachan 1 - 26th August 2019",
                  "Day 2 - Pravachan 2 - 27th August 2019",
                  "Day 3 - Pravachan 3 - 28th August 2019",
                  "Day 4 - Pravachan 4 - 29th August 2019",
                  "Day 6 - Pravachan 5 - 31st August 2019",
                  "Day 7 - Pravachan 6 - 1st September 2019",
                  "Day 8 - Pravachan 7 - 2nd September 2019"]
<<<<<<< HEAD
    """

    #data_dir = "../../../data/paryushan-2019"
    data_dir = "../../../data/2019-shri-yogvasishtha-maharamayan"
    audios_sph_to_transcript_map = read_mapping_file(data_dir)
=======
    data_dir = "../../../data/paryushan-2019"
    """
    #inp_dnames = [""]
    data_dir = "../../../data/2019-shri-yogvasishtha-maharamayan"
    
    audios_sph_to_transcript_map = read_jsonl_file(os.path.join(data_dir, "audios_sph_transcripts_map.json"))
>>>>>>> ddbc529ab281207219fa7d29347afa192a40974d

    out_sph_dname        = os.path.join(data_dir, "segmented-audio-sph")
    out_transcript_dname = os.path.join(data_dir, "segmented-transcripts")

<<<<<<< HEAD
=======
    ##### SETUP #####
>>>>>>> ddbc529ab281207219fa7d29347afa192a40974d
    for dname in [out_sph_dname, out_transcript_dname]:
        empty_dir(dname)
        if not os.path.exists(dname):
            os.makedirs(dname)
<<<<<<< HEAD

    for inp_sph_fname,inp_transcript_fname in audios_sph_to_transcript_map.items():
        if inp_transcript_fname[-3:]=="doc":
            print("ignoring .doc transcript")
            continue
        this_out_sph_dname        = os.path.join(out_sph_dname, remove_first_dir(os.path.dirname(inp_sph_fname)))
        this_out_transcript_dname = os.path.join(out_transcript_dname, remove_first_dir(os.path.dirname(inp_transcript_fname)))
        for dname in [this_out_sph_dname, this_out_transcript_dname]:
            if not os.path.exists(dname):
                os.makedirs(dname)

        inp_sph_fname        = os.path.join(data_dir, inp_sph_fname)
        inp_transcript_fname = os.path.join(data_dir, inp_transcript_fname)
            
        transcript_segments = get_transcript_segments(inp_transcript_fname) # list. each elem is (start_time, end_time, text). times are in seconds.
        write_segmented_sphs(inp_sph_fname, transcript_segments, this_out_sph_dname)
        write_segmented_transcripts(transcript_segments, this_out_transcript_dname)
=======

    for entry in audios_sph_to_transcript_map:
        inp_sph_fname        = os.path.join(data_dir, entry["audio_sph_file"])
        inp_transcript_fname = os.path.join(data_dir, entry["transcript_file"])
        filter_criteria      = entry["filter_criteria"]
>>>>>>> ddbc529ab281207219fa7d29347afa192a40974d

        ##### RUN #####
        transcript_segments = get_transcript_segments(inp_transcript_fname) # list. each elem is (start_time, end_time, text). times are in seconds.
        write_segmented_sphs(inp_sph_fname, transcript_segments, out_sph_dname)
        write_segmented_transcripts(transcript_segments, out_transcript_dname)
    
