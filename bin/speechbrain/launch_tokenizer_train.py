import os
import json
import argparse
import tempfile

from hyperpyyaml import load_hyperpyyaml
from speechbrain.tokenizers.SentencePiece import SentencePiece

from utils import get_utterance_manifest_from_data_config



def create_transcripts_json(corpus):
    """
    INPUT:
    corpus: list of entries from .jsonl files. [{"audo_sph_file": ..., "transcript_all_file": ..., "transcript_uid": ..., "filter_criteria": ...}, ...]
    """

    unique_transcript_all_files = list(set([entry["transcript_all_file"] for entry in corpus]))

    ### Get Transcript Map for all entries in Transcript-All Files
    # key = transcript uid
    # value = transcript line
    # <s> અંબાલાલ ભાઈને ચાર વાર ભલામણ કરી છે ત્રિભોવનભાઇ ને બે વાર ભલામણ કરી છે </s> (b0d740f0-speaker1-00f44130)
    transcript_map = {}
    for transcript_all_file in unique_transcript_all_files:
        with open(transcript_all_file, "r") as f:
            for line in f:
                utt_id = line.split("</s>")[-1].strip()[1:-1]
                transcript = line.split("<s>")[-1].split("</s>")[0].strip()
                transcript_map[utt_id] = transcript

    ### Get Transcripts for selected entries in Transcript-All Files (i.e. the corpus)
    selected_transcripts_json = {}
    annotation_read = "transcript"
    for entry in corpus:
        key = entry["transcript_uid"]
        assert key in transcript_map
        selected_transcripts_json[key] = {annotation_read: transcript_map[key]}
    
    return selected_transcripts_json, annotation_read


def main(config):
    ### get Train Data ###
    # list of {'audio_sph_file': str, 'transcript_all_file': str, 'transcript_uid': str, 'filter_criteria': str}
    # meaning that <audio_sph_file>'s transcript is the onoe in the <transcript_all_file> with id <transcript_uid>
    train_corpus = get_utterance_manifest_from_data_config(config.train_data_config)
    for x in train_corpus:
        assert os.path.exists(x["transcript_all_file"]), "data transcript file {} does not exist! Exiting!".format(x["transcript_all_file"])
    
    ### create json file for SpeechBrain-->SentencePiece ###
    selected_transcripts_json, annotation_read = create_transcripts_json(train_corpus)

    ### train custom SentencePiece Tokenizer ###
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as f:
        f.write(json.dumps(selected_transcripts_json))
        f.seek(0) 

        SentencePiece(model_dir                = config.output_folder,
                      vocab_size               = config.vocab_size,
                      annotation_train         = f.name,
                      annotation_read          = annotation_read,
                      annotation_format        = "json",
                      model_type               = config.model_type,
                      character_coverage       = config.character_coverage,
                      annotation_list_to_check = config.annotation_list_to_check)


def argparser():
    parser = argparse.ArgumentParser()

    ## DATA ##
    parser.add_argument("--train_data_config", type=str, required=True)
    

    ## TOKENIZER ##
    parser.add_argument("--output_folder", type=str, required=True)
    parser.add_argument("--vocab_size", type=int, required=True)
    parser.add_argument("--model_type", type=str, required=True, choices=["unigram", "bpe", "char"])
    parser.add_argument("--character_coverage", type=float, required=True, help="Amount of characters covered by the model "
                                                                "good defaults are: 0.9995 for languages with a rich character set like Japanese or Chinese "
                                                                "and 1.0 for other languages with small character set.")
    parser.add_argument("--annotation_list_to_check", type=str, nargs="+", required=True, help="List of the annotation file which is used for checking "
                                                                                               "the accuracy of recovering words from the tokenizer.")
    return parser.parse_args()



if __name__=="__main__":
    ##### CONFIG #####
    config = argparser()

    ##### #####
    main(config)
