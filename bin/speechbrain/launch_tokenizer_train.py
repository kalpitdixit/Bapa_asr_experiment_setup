import os
import json
import argparse
import tempfile

from hyperpyyaml import load_hyperpyyaml
from speechbrain.tokenizers.SentencePiece import SentencePiece

from utils import load_hparams, get_utterance_manifest_from_datasets, write_hyperpyyaml_file



def main(config):
    ### get Train Data ###
    # list of {'audio_sph_file': str, 'transcript_all_file': str, 'transcript_uid': str, 'filter_criteria': str}
    # meaning that <audio_sph_file>'s transcript is the one in the <transcript_all_file> with id <transcript_uid>
    hparams = load_hparams(config.train_data_config)
    train_corpus = get_utterance_manifest_from_datasets(hparams["datasets"])
    
    ### create json file for SpeechBrain-->SentencePiece ###
    annotation_read = "transcript" # key-name for each `entry` in `train_corpus` having the transcript as its value

    ### write config file
    write_hyperpyyaml_file(os.path.join(config.output_folder, "sp_vocab_{}_{}.yaml".format(config.vocab_size, config.model_type)),
                           {"model_dir": config.output_folder,
                            "vocab_size": config.vocab_size,
                            "model_type": config.model_type,
                            "sp_model_file": os.path.join(config.output_folder, "{}_{}.model".format(str(config.vocab_size), config.model_type)),
                            "unk_index": config.unk_index,
                            "bos_index": config.bos_index,
                            "eos_index": config.eos_index,
                            "pad_index": config.pad_index})



    ### train custom SentencePiece Tokenizer ###
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as f:
        f.write(json.dumps(dict([(entry["transcript_uid"], {annotation_read: entry["transcript"]}) for entry in train_corpus])))
        f.seek(0) 

        SentencePiece(model_dir                = config.output_folder,
                      vocab_size               = config.vocab_size,
                      annotation_train         = f.name,
                      annotation_read          = annotation_read,
                      annotation_format        = "json",
                      unk_id                   = config.unk_index,
                      bos_id                   = config.bos_index,
                      eos_id                   = config.eos_index,
                      pad_id                   = config.pad_index,
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

    ## SPECIAL TOKENS ##
    parser.add_argument("--unk_index", type=int, default=0) 
    parser.add_argument("--bos_index", type=int, default=1) 
    parser.add_argument("--eos_index", type=int, default=2) 
    parser.add_argument("--pad_index", type=int, default=3) 
    return parser.parse_args()



if __name__=="__main__":
    ##### CONFIG #####
    config = argparser()

    ##### #####
    main(config)
