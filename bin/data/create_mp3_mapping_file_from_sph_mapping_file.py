import os
import argparse
import docx
import uuid
import json

from utils import read_jsonl_file, write_jsonl_file, empty_dir, convert_to_seconds, get_hash




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


def write_segmented_wavs_and_transcripts(data_dir, inp_sph_fname, transcript_segments, out_wav_dname, out_transcript_dname, entryi, sox_tfm):
    out_transcript_fname    = os.path.join(out_transcript_dname, "all.transcriptions")
    out_segmented_map_fname = os.path.join(data_dir, "segmented_audios_wav_transcripts_map.json")

    with open(out_transcript_fname, "a") as fw, open(out_segmented_map_fname, "a") as fw_map:
        for i,seg in enumerate(transcript_segments):
            stime, etime, transcript, uid = seg[:]

            ## WAV
            out_wav_fname = os.path.join(out_wav_dname, "{}.wav".format(uid))
            sox_tfm.trim(stime, etime).build_file(inp_sph_fname, out_wav_fname)
            print(uid, stime, etime, inp_sph_fname, out_wav_fname)
            if i >= 10:
                exit()
            continue

            ### Transcript
            out_str = "<s> {} </s> ({})".format(transcript, uid)
            fw.write(out_str+"\n")

            ## Segmented Map
            segmented_entry = {"audio_wav_file"     : os.path.relpath(out_wav_fname, data_dir),
                               "transcript_all_file": os.path.relpath(out_transcript_fname, data_dir),
                               "transcript_uid"     : uid,
                               "filter_criteria"    : entry["filter_criteria"]}
            fw_map.write(json.dumps(segmented_entry)+"\n")


def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audios_sph_to_transcript_fname", type=str, default=None, required=True)
    return parser.parse_args()



if __name__=="__main__":
    """
    this script converts an `audios_SPH_to_transcript` file to an `audios_MP3_to_transcript` file
    no new creation or segmentation of audio files is involved
    this script checks for the presence of a MP3 file named the same as the corresponding SPH file

    ASSUMES:
        that the mp3 files will be present in the `audio-mp3` folder from the dir containing the sph mapping file
        i.e.
        root
        |-- audios_sph_to_transcript_map.json
        |-- audio-sph
            |-- sph1
            |-- sph2
            |-- .
            |-- .
        |-- audio-mp3
            |-- mp31
            |-- mp32
            |-- .
            |-- .
    
    USAGE:
        python create_mp3_mapping_file_from_sph_mapping_file.py --audios_sph_to_transcript_fname /path/to/

    OUTPUT:
        a `audios_MP3_to_transcript` file

    """
    ##### ARGUMENTS #####
    AUDIOS_MP3_TO_TRANSCRIPT_FNAME = "audios_mp3_to_transcript_fname.json"

    config = argparser()
    audios_mp3_to_transcript_fname = os.path.join(os.path.dirname(config.audios_sph_to_transcript_fname), AUDIOS_MP3_TO_TRANSCRIPT_FNAME)

    ##### READ #####
    data_dir = os.path.dirname(config.audios_sph_to_transcript_fname)
    audios_sph_to_transcript_map = read_jsonl_file(config.audios_sph_to_transcript_fname)
    audios_mp3_to_transcript_map = []

    ##### RUN #####
    print(len(audios_sph_to_transcript_map))
    found = 0
    for entry in audios_sph_to_transcript_map:
        audio_sph_file = entry["audio_sph_file"]
        assert audio_sph_file[-4:]==".sph"

        audio_mp3_file = os.path.basename(entry["audio_sph_file"])[:-4]+".mp3"
        audio_mp3_file = os.path.join("audio-mp3", audio_mp3_file)
        
        #assert os.path.exists(os.path.join(data_dir, audio_mp3_file))
        if os.path.exists(os.path.join(data_dir, audio_mp3_file)):
            del entry["audio_sph_file"]
            entry["audio_mp3_file"] = audio_mp3_file 
            audios_mp3_to_transcript_map.append(entry)

    ##### WRITE #####
    write_jsonl_file(audios_mp3_to_transcript_fname, audios_mp3_to_transcript_map)
