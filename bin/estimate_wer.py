import sys



class WER(object):
    def __init__(self):
        self.ref_words = 0
        self.errors = 0
        pass

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
        ref_words = self.get_words(ex["ref"])
        hyp_words = self.get_words(ex["hyp"])

        ex_wer = wer(ref_words, hyp_words)
        self.ref_words += len(ref_words)
        self.errors += ex_wer
        pass

    def print_metrics(self):
        wer = 100. * self.errors / self.ref_words
        print("# Ref Words: {:,d}".format(self.ref_words))
        print("# Errors   : {:,d}".format(self.errors))
        print("    WER    : {:.2f}".format(wer))



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


def run(fname):
    wer = WER()

    with open(fname, "r") as f:
        in_ex = False
        for line in f:
            if line[:3]=="id:":
                in_ex = True
                ex = {}
            if not in_ex:
                continue

            if line[:7]=="Scores:":
                ex["scores"] = line
            elif line[:4]=="REF:":
                ex["ref"] = read_ref_hyp_line(line)
            elif line[:4]=="HYP:":
                ex["hyp"] = read_ref_hyp_line(line)
            elif line=="\n":
                wer.update(ex)
                in_ex = False
    wer.print_metrics()



if __name__=="__main__":
    fname = sys.argv[1]

    run(fname)
