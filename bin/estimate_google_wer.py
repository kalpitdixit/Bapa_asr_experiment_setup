import sys
import re
import docx
import ujson as json
import uuid
import hashlib


time_pattern = re.compile("\d\d:\d\d:\d\d", re.ASCII)
punctuations = [".", ",", "!", "?"]


def get_hash(s):
    h = hashlib.sha1()
    h.update(s.encode("utf-8"))
    return h.hexdigest()


class WER(object):
    def __init__(self):
        self.ref_words = 0
        self.errors = 0
        self.ref_length_dist = []
        self.errors_dist = []

    def get_words(self, chars):
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

    def update(self, ex):
        #ref_words = self.get_words(ex["ref"])
        #hyp_words = self.get_words(ex["hyp"])
        ref_words = ex["ref"].split(" ")
        hyp_words = ex["hyp"].split(" ")

        ex_wer = wer(ref_words, hyp_words)
        self.ref_words += len(ref_words)
        self.errors += ex_wer

        self.ref_length_dist.append(len(ref_words))
        self.errors_dist.append(ex_wer)

    def print_metrics(self):
        wer = 100. * self.errors / self.ref_words
        print()
        print("# Ref Words: {:,d}".format(self.ref_words))
        print("# Errors   : {:,d}".format(self.errors))
        print("    WER    : {:.2f}".format(wer))


    def write_word_output_to_file(self, exs):
        with open("tmp_word_output.txt", "w") as fw:
            for ex in exs:
                ref_words = self.get_words(ex["ref"])
                hyp_words = self.get_words(ex["hyp"])

                ref_words = [x.replace("**", "") for x in ref_words]
                hyp_words = [x.replace("**", "") for x in hyp_words]
                print(ex["id"])
                print(" ".join(ref_words))
                print(" ".join(hyp_words))
                print()

                out_json = {"id": ex["id"], "ref": ref_words, "hyp": hyp_words}
                fw.write(json.dumps(out_json, sort_keys=True)+"\n")





def wer(r, h):
    """
    Calculation of WER with Levenshtein distance.

    Works only for iterables up to 254 elements (uint8).
    O(nm) time ans space complexity.

    Parameters
    ----------
    r : list
    h : list

    Returns
    -------
    int

    Examples
    --------
    >>> wer("who is there".split(), "is there".split())
    1
    >>> wer("who is there".split(), "".split())
    3
    >>> wer("".split(), "who is there".split())
    3
    """
    # initialisation
    import numpy

    d = numpy.zeros((len(r) + 1) * (len(h) + 1), dtype=numpy.uint8)
    d = d.reshape((len(r) + 1, len(h) + 1))
    for i in range(len(r) + 1):
        for j in range(len(h) + 1):
            if i == 0:
                d[0][j] = j
            elif j == 0:
                d[i][0] = i

    # computation
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            if r[i - 1] == h[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                substitution = d[i - 1][j - 1] + 1
                insertion = d[i][j - 1] + 1
                deletion = d[i - 1][j] + 1
                d[i][j] = min(substitution, insertion, deletion)

    return d[len(r)][len(h)]


def read_ref_hyp_line(line):
    chars = []
    for x in line.strip().split(" ")[1:]:
        if x=="":
            continue
        elif x=="<space>":
            x = "<SPACE>"
        chars.append(x)
    return chars


def convert_to_seconds(s):
    assert len(s)==8, "expected len(s) to be 8, but got len {}: {}".format(len(s), s)
    assert time_pattern.match(s)
    return float(s[0:2])*3600 + float(s[3:5])*60 + float(s[6:8])


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


def get_transcripts(google_fname, gold_fname):
    goog_ts = get_transcript_segments(google_fname)
    gold_ts = get_transcript_segments(gold_fname)

    print(goog_ts[0])
    print(gold_ts[0])
    print()
    print(goog_ts[-1])
    print(gold_ts[-1])

    A = []
    B = []

    ptr_a = 0
    ptr_b = 0
    
    while ptr_a < len(goog_ts) and ptr_b < len(gold_ts):
        if goog_ts[ptr_a][0] == gold_ts[ptr_b][0] and goog_ts[ptr_a][1] == gold_ts[ptr_b][1]:
            A.append(goog_ts[ptr_a])
            B.append(gold_ts[ptr_b])
            ptr_a += 1
            ptr_b += 1
        elif goog_ts[ptr_a][1] < gold_ts[ptr_b][0]:
            ptr_a += 1
        elif goog_ts[ptr_a][0] > gold_ts[ptr_b][1]:
            ptr_b += 1
        else:
            ptr_a += 1
            ptr_b += 1

    assert len(A) == len(B)

    print("# Orig Goog : {}".format(len(goog_ts)))
    print("# Orig Gold : {}".format(len(gold_ts)))
    print("# Matches   : {}".format(len(A)))

    goog_ts = A[:]
    gold_ts = B[:]

    assert len(goog_ts)==len(gold_ts), "{} vs {}".format(len(goog_ts), len(gold_ts))
    
    for a,b in zip(goog_ts, gold_ts):
        assert a[0]==b[0]
        assert a[1]==b[1]

    return goog_ts, gold_ts


def run(google_fname, gold_fname):
    goog_ts, gold_ts = get_transcripts(google_fname, gold_fname)

    wer = WER()

    for a,b in zip(goog_ts, gold_ts):
        ex = {"ref": a[2],
              "hyp": b[2]}
        wer.update(ex)
                
    wer.print_metrics()



if __name__=="__main__":
    google_fname = sys.argv[1]
    gold_fname   = sys.argv[2]

    run(google_fname, gold_fname)
