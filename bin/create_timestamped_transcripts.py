import argparse
import json




def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("asr_output", type=str, help="path to output of ASR model i.e. `result.txt`")
    parser.add_argument("segment_timestamps", type=str, help="file containing start and end timestamps for each segment id")
    parser.add_argument("--output_fname", type=str)
    return parser.parse_args()


def hhmmss_to_ss(strng):
    a, b, c = [float(x) for x in strng.split(":")]
    ss = a*3600+b*60+c
    return ss


def read_segment_timestamps_file(fname):
    seg2ts = {}
    with open(fname, "r") as f:
        for line in f:
            line = line.strip().split(" ")
            if ":" in line[1]:
                start = hhmmss_to_ss(line[1])
                end   = hhmmss_to_ss(line[2])
            else:
                start = float(line[1])
                end   = float(line[2])
            seg2ts[line[0].split("-")[0]] = {"start": start,
                                             "end"  : end}
    return seg2ts


def read_ref_hyp_line(line):
    chars = []
    for x in line.strip().split(" ")[1:]:
        if x=="":
            continue
        elif x=="<space>":
            x = "<SPACE>"
        chars.append(x)
    words = get_words(chars)
    words = [w.replace("*","") for w in words]
    return words


def get_words(chars):
        words = []
        start_ind = 0
        while start_ind < len(chars):
            try:
                end_ind = chars.index("<SPACE>", start_ind)
            except ValueError:
                end_ind = len(chars)
            words.append("".join(chars[start_ind:end_ind]))
            start_ind = end_ind + 1
        return words


def read_asr_output_file(fname):
    seg2asrout = {}
    with open(fname, "r") as f:
        seg = {}
        in_ex = False
        for line in f:
            if line[:3]=="id:":
                seg["segment_id"] = line.strip().split(" ")[-1][1:-1].split("-")[-1]
                in_ex = True
            if not in_ex:
                continue

            if line[:4]=="HYP:":
                seg["hyp"] = read_ref_hyp_line(line)
            elif line=="\n":
                in_ex = False
                seg2asrout[seg["segment_id"]] = {"asr_output": seg["hyp"]}
                seg = {}
    return seg2asrout



if __name__=="__main__":
    ##### ARGS #####
    args = argparser()
    
    ##### READ #####
    seg2ts     = read_segment_timestamps_file(args.segment_timestamps)
    seg2asrout = read_asr_output_file(args.asr_output)
    print(len(seg2ts)) 
    print(len(seg2asrout)) 

    ##### COMBINE TIMESTAMPS and ASR OUTPUTS #####

    for k in seg2ts:
        if k not in seg2asrout:
            print(k)
    assert len(seg2ts)==len(seg2asrout)

    for k in seg2ts:
        assert k in seg2asrout
        seg2asrout[k]["start_time"] = seg2ts[k]["start"]
        seg2asrout[k]["end_time"]   = seg2ts[k]["end"]
    
    ##### WRITE OUTPUT #####
    if args.output_fname:
        with open(args.output_fname, "w") as fw:
            for k,v in seg2asrout.items():
                print(v)
                fw.write(json.dumps(v, sort_keys=True)+"\n")
