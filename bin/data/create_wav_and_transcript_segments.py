import os
import argparse
import sox
import re
import docx
import uuid
import json

from utils import read_jsonl_file, empty_dir, convert_to_seconds, get_hash

punctuations = [".", ",", "!", "?"]



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


def write_segmented_wavs_and_transcripts(data_dir, inp_sph_fname, transcript_segments, out_wav_dname, out_transcript_dname, entryi, sox_tfm, write_to_disk):
    out_transcript_fname    = os.path.join(out_transcript_dname, "all.transcriptions")
    out_segmented_map_fname = os.path.join(data_dir, "segmented_audios_wav_transcripts_map.json")

    with open(out_transcript_fname, "a") as fw, open(out_segmented_map_fname, "a") as fw_map:
        for i,seg in enumerate(transcript_segments):
            stime, etime, transcript, uid = seg[:]

            ## WAV
            out_wav_fname = os.path.join(out_wav_dname, "{}.wav".format(uid))
            if write_to_disk:
                sox_tfm.trim(stime, etime).build_file(inp_sph_fname, out_wav_fname)
            #print(uid, stime, etime, inp_sph_fname, out_wav_fname)
            #if i >= 10:
            #    exit()
            #continue

            ### Transcript
            out_str = "<s> {} </s> ({})".format(transcript, uid)
            if write_to_disk:
                fw.write(out_str+"\n")

            ## Segmented Map
            segmented_entry = {"audio_wav_file"     : os.path.relpath(out_wav_fname, data_dir),
                               "transcript_all_file": os.path.relpath(out_transcript_fname, data_dir),
                               "transcript_uid"     : uid,
                               "filter_criteria"    : entry["filter_criteria"]}
            if write_to_disk:
                fw_map.write(json.dumps(segmented_entry)+"\n")


def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audios_sph_to_transcript_fname", type=str, default=None)
    parser.add_argument("--write_to_disk", action="store_true")
    return parser.parse_args()



if __name__=="__main__":
    """
    a script which uses existing audios_SPH_to_transcript files and creates SEGMENTED_audios_WAV_to_transcript files
                                                and creates the wav files themselves
                                                and creates it all in a segmented manner as per the transcript files
    
    USAGE:
        python create_wav_and_transcript_segments.py --audios_sph_to_transcript_fname /path/to/

    OUTPUT:
         
    """
    ##### ARGUMENTS #####
    config = argparser()

    assert config.audios_sph_to_transcript_fname is not None

    data_dir = os.path.dirname(config.audios_sph_to_transcript_fname)
    audios_sph_to_transcript_map = read_jsonl_file(config.audios_sph_to_transcript_fname)

    out_wav_dname        = os.path.join(data_dir, "segmented-audio-wav")
    out_transcript_dname = os.path.join(data_dir, "segmented-transcripts")

    for dname in [out_wav_dname, out_transcript_dname]:
        empty_dir(dname, allow_data_folder_deletion=True)
        if not os.path.exists(dname):
            os.makedirs(dname)

    ##### SOX Transformer  #####
    sox_tfm = sox.Transformer()

    ##### RUN #####
    for entry in audios_sph_to_transcript_map:
        inp_sph_fname        = os.path.join(data_dir, entry["audio_sph_file"])
        inp_transcript_fname = os.path.join(data_dir, entry["transcript_file"])
        filter_criteria      = entry["filter_criteria"]
        print(entry)
        ###
        transcript_segments = get_transcript_segments(inp_transcript_fname) # list. each elem is (start_time, end_time, text). times are in seconds.
        write_segmented_wavs_and_transcripts(data_dir, inp_sph_fname, transcript_segments, out_wav_dname, out_transcript_dname, entry, sox_tfm, config.write_to_disk)

