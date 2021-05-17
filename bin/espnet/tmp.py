import os
import glob
import docx
import re
import hashlib
import uuid
import json
from constants import DATA_DIR, KALDI_DIR



if __name__=="__main__":
    ##### ARGUMENTS #####
    #inp_sph_fname        = sys.argv[1] # /home/ubuntu/data/paryushan-2019/audios-sph/Day 1 - Pravachan 1 - 26th August 2019
    #inp_transcripts_fname = sys.argv[2] # Pr1-Part 1-PTK522-PARYUSHAN2019-26082019-Atm. Sonalben-10092019.docx

    #inp_dname = "Day 2 - Pravachan 2 - 27th August 2019"
    #inp_dname = "Day 1 - Pravachan 1 - 26th August 2019"

    inp_dnames = ["Day 1 - Pravachan 1 - 26th August 2019",
                  "Day 2 - Pravachan 2 - 27th August 2019",
                  "Day 3 - Pravachan 3 - 28th August 2019",
                  "Day 4 - Pravachan 4 - 29th August 2019",
                  "Day 6 - Pravachan 5 - 31st August 2019",
                  "Day 7 - Pravachan 6 - 1st September 2019",
                  "Day 8 - Pravachan 7 - 2nd September 2019"]

    audio_transcript_map = []
    for inp_dname in inp_dnames:
        inp_sph_dname        = "../../../data/paryushan-2019/audios-sph/{}".format(inp_dname)
        inp_transcript_dname = "../../../data/paryushan-2019/transcripts/{}".format(inp_dname)
        
        out_sph_dname        = "../../../data/paryushan-2019/segmented-audio-sph/{}".format(inp_dname)
        out_transcript_dname = "../../../data/paryushan-2019/segmented-transcripts/{}".format(inp_dname)

        ##### RUN #####
        inp_sph_fnames        = sorted(glob.glob(os.path.join(inp_sph_dname, "*")))
        inp_transcript_fnames = sorted(glob.glob(os.path.join(inp_transcript_dname, "*docx")))

        audio_sph_props = {}
        for y in inp_sph_fnames:
            # "Patrank-522-Pravachan-7-Part-2.sph"
            x = os.path.basename(y)
            pravachan = x.split("-")[3]
            part      = x.split("-")[5][:-4]
            if not pravachan in audio_sph_props:
                audio_sph_props[pravachan] = {}
            audio_sph_props[pravachan][part] = os.path.join(os.path.basename(os.path.dirname(os.path.dirname(y))),
                                                            os.path.basename(os.path.dirname(y)),
                                                            os.path.basename(y))

        inp_transcript_props = {}
        for y in inp_transcript_fnames:
            # "Pr7-Part 3-PTK522-PARYUSHAN2019-02092019-Rina-09092019.docx"
            x = os.path.basename(y)
            pravachan = x.split("-")[0][2:]
            part      = x.split("-")[1].split(" ")[1]
            if not pravachan in inp_transcript_props:
                inp_transcript_props[pravachan] = {}
            inp_transcript_props[pravachan][part] = os.path.join(os.path.basename(os.path.dirname(os.path.dirname(y))),
                                                                 os.path.basename(os.path.dirname(y)),
                                                                 os.path.basename(y))
    
        
        for k,v in audio_sph_props.items():
            if k in inp_transcript_props:
                v2 = inp_transcript_props[k]
                for kk in v:
                    if kk in v2:
                        audio_transcript_map.append([v[kk], v2[kk]])
                        print(v[kk])
                        print(v2[kk])
                        print()
           
    ##### WRITE #####
    with open("audios_sph_transcripts_map.json", "w") as fw:
        for x in audio_transcript_map:
            y = {"audio_sph_file": x[0], "transcript_file": x[1]}
            fw.write(json.dumps(y, sort_keys=True)+"\n")
     
