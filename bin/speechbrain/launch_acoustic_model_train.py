import os
import json
import argparse
import tempfile
from collections import OrderedDict, Counter
from hyperpyyaml import load_hyperpyyaml, dump_hyperpyyaml
import torch

import speechbrain as sb
import sentencepiece as sp

from utils import get_utterance_manifest_from_datasets, load_hparams, write_hyperpyyaml_file, combine_multiple_hyperpyyaml_files_into_one
from asr import ASR


def convert_data_config_to_sb_dataset(data_config):
    """
        data_config: from yaml file, supporting key "datasets" with value: list of {"map_file": str, "filter_criterias": list of str}
        1. data_config --> corpus. list of {'audio__file': str, 'transcript_all_file': str, 'transcript_uid': str, 'filter_criteria': str}
        2. corpus --> json format of the same for SpeechBrain
        3. json format of the same for SpeechBrain --> write to tmp file
        4. tmp file --> DynamicItemDataset.from_json
    """
    corpus = get_utterance_manifest_from_datasets(data_config["datasets"])
    # convert corpus into a single json object
    corpus_json = dict([(line["transcript_uid"].split("-")[2], line) for line in corpus]) 
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as f:
        f.write(json.dumps(corpus_json))
        f.seek(0)
 
        data = sb.dataio.dataset.DynamicItemDataset.from_json(json_path=f.name)
    return data


# Define custom data procedure
def dataio_prepare(hparams):
    """
    It also defines the data processing pipeline through user-defined functions.
    """
    # train dataset
    train_data = convert_data_config_to_sb_dataset(hparams["train_data_config"])

    # valid dataset
    valid_data = convert_data_config_to_sb_dataset(hparams["valid_data_config"])
    #valid_data = valid_data.filtered_sorted(sort_key="duration")

    # test datasets - separate
    test_data = convert_data_config_to_sb_dataset(hparams["test_data_config"])
    """
    test_datasets = {}
    for csv_file in hparams["test_csv"]:
        name = Path(csv_file).stem
        test_datasets[name] = sb.dataio.dataset.DynamicItemDataset.from_csv(
            csv_path=csv_file, replacements={"data_root": data_folder}
        )
        test_datasets[name] = test_datasets[name].filtered_sorted(
            sort_key="duration"
        )
    """

    datasets = [train_data, valid_data] + [test_data]

    tokenizer = sp.SentencePieceProcessor()
    tokenizer.load(hparams["tokenizer_config"]["sp_model_file"])

    # 2. Define audio pipeline:
    @sb.utils.data_pipeline.takes("audio_wav_file")
    @sb.utils.data_pipeline.provides("sig")
    def audio_pipeline(audio_wav_file):
        sig = sb.dataio.dataio.read_audio(audio_wav_file)
        return sig
    
    sb.dataio.dataset.add_dynamic_item(datasets, audio_pipeline)


    # 3. Define text pipeline:
    @sb.utils.data_pipeline.takes("transcript")
    @sb.utils.data_pipeline.provides(
        "transcript", "tokens_list", "tokens_bos", "tokens_eos", "tokens"
    )
    def text_pipeline(transcript):
        yield transcript
        tokens_list = tokenizer.encode_as_ids(transcript)
        yield tokens_list
        tokens_bos = torch.LongTensor([hparams["tokenizer_config"]["bos_index"]] + (tokens_list))
        yield tokens_bos
        tokens_eos = torch.LongTensor(tokens_list + [hparams["tokenizer_config"]["eos_index"]])
        yield tokens_eos
        tokens = torch.LongTensor(tokens_list)
        yield tokens

    sb.dataio.dataset.add_dynamic_item(datasets, text_pipeline)

    # 4. Set output:
    sb.dataio.dataset.set_output_keys(
        datasets, ["id", "sig", "transcript", "tokens_bos", "tokens_eos", "tokens"],
    )

    return train_data, valid_data, test_data, tokenizer
   
 
def main(config):
    ### create Experiment Directory ###
    # combine all hyperparameters into a single file
    hparams = load_hparams(config.exp_config)
    hparams["model_config"] = load_hparams(config.model_config)

    # create exp dir
    sb.create_experiment_directory(
        experiment_directory=config.output_folder,
        hyperparams_to_save=config.exp_config,
        overrides=None
    )

    ### Datasets and Tokenizer ###
    train_data, valid_data, test_data, tokenizer = dataio_prepare(hparams)


    # Trainer initialization
    run_opts = {"device": "cuda:0"} # certain args from yaml file will autoamtically get picked as run_opts
                                 # see https://github.com/speechbrain/speechbrain/blob/develop/recipes/LibriSpeech/ASR/transformer/train.py#L372
                                 # see https://github.com/speechbrain/speechbrain/blob/d6adc40e742107c34ae38dc63484171938b4d237/speechbrain/core.py#L124
    #print(type(hparams["model_config"]["modules"]))
    #print(type(hparams))
    #exit()
    asr_brain = ASR(
        modules=hparams["model_config"]["modules"],
        opt_class=hparams["model_config"]["Adam"],
        hparams=hparams["model_config"],
        run_opts=run_opts,
        checkpointer=hparams["model_config"]["checkpointer"],
    )

    # adding objects to trainer:
    asr_brain.tokenizer = tokenizer # hparams["tokenizer"]

    # Training
    asr_brain.fit(
        asr_brain.hparams.epoch_counter,
        train_data,
        valid_data,
        train_loader_kwargs=hparams["model_config"]["train_dataloader_opts"],
        valid_loader_kwargs=hparams["model_config"]["valid_dataloader_opts"],
    )

    


    raise NotImplementedError

    ### get Train Data ###
    # list of {'audio__file': str, 'transcript_all_file': str, 'transcript_uid': str, 'filter_criteria': str}
    # meaning that <audio__file>'s transcript is the one in the <transcript_all_file> with id <transcript_uid>
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
    parser.add_argument("--valid_data_config", type=str, required=True)
    parser.add_argument("--test_data_config", type=str, required=True)

    ## TOKENIZER ##
    parser.add_argument("--tokenizer_config", type=str, required=True)

    ## TASK MODEL ##
    parser.add_argument("--model_config", type=str, required=True)

    ## COMBINED ARGS ##
    # this is a bit abusive, various hyperpyyaml configs are kept separate to prevent combinatorial explosion of yaml files
    # this file will be create during runtime by combining all input config files as a step 1
    parser.add_argument("--exp_config", type=str, default="tmp.am_exp_config.yaml", choices=["tmp.am_exp_config.yaml"])
    
    ## OUTPUT ##
    parser.add_argument("--output_folder", type=str, required=True)
    return parser.parse_args()



if __name__=="__main__":
    """
    TODOs:
        1. add model_config to the saved per-exp config
        2. use the same single-yaml file input thing as LibriSpeech recipe
          a. find way to give other yaml files as inputs to yaml file and then make the data yaml file a parameter in the main yaml file
    """
    ##### CONFIG #####
    config = argparser()
    combine_multiple_hyperpyyaml_files_into_one(input_hyperpyyaml_files = {"train_data_config": config.train_data_config,
                                                                           "valid_data_config": config.valid_data_config,
                                                                           "test_data_config" : config.test_data_config,
                                                                           "tokenizer_config" : config.tokenizer_config},
                                                output_hyperpyyaml_file = config.exp_config)
    ##### #####
    main(config)
