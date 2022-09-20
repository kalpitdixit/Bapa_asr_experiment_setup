import os
import json
import argparse
import tempfile
import uuid
from collections import OrderedDict, Counter
from hyperpyyaml import load_hyperpyyaml, dump_hyperpyyaml
import torch
import numpy as np

import speechbrain as sb
from speechbrain.utils.distributed import run_on_main
import sentencepiece as sp

from utils import get_utterance_manifest_from_datasets, load_hparams, write_hyperpyyaml_file, combine_multiple_hyperpyyaml_files_into_one
from asr import ASR
from constants import RESULTS


def convert_data_config_to_sb_dataset(data_config):
    """
        data_config: from yaml file, supporting key "datasets" with value: list of {"map_file": str, "filter_criterias": list of str}
        1. data_config --> corpus. list of {'audio_file': str, 'transcript_all_file': str, 'transcript_uid': str, 'filter_criteria': str}
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
    print("len(train_data) : ", len(train_data))

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


def filter_sequences_by_length(data, split_name):
    full_size = len(data)
    data = data.filtered_sorted(key_test={"sig": lambda a: 640 * 10 <= list(a.size())[0] <= 640 * 4000})
    print(f"removing short and long sequences from {split_name.upper()}: dataset size {full_size} --> {len(data)}")
    print("keeping only signals that meet: 10 <= sig / 640 >= 4000")
    return data
   
 
def main(config):
    ### create Experiment Directory ###
    # output folder
    if config.run_test_only:
        config.output_folder = config.output_folder # os.path.join(RESULTS, config.output_folder, f"{config.seed}")
    else:
        config.output_folder = os.path.join(RESULTS, config.output_folder, f"seed_{config.seed}_{str(uuid.uuid4())[:8]}")
        print(f"output_folder: {config.output_folder}")

    # combine all hyperparameters into a single file
    hparams = load_hparams(config.exp_config)
    hparams["model_config"] = load_hparams(config.model_config, overrides={"seed": config.seed, "output_folder": config.output_folder})
    #print(hparams["test_search"])
    #exit()
    #hparams["model_config"]["output_folder"] = "results/transformer/seed_8886"
    #print(hparams["model_config"]["output_folder"])
    #print(hparams["model_config"]["wer_file"])
    #exit()

    # reset hparams locations to store
    """
    hparams["model_config"]["output_folder"] = os.path.join(config.output_folder, f"seed_{hparams['model_config']['seed']}")
    hparams["model_config"]["wer_file"] = os.path.join(hparams["model_config"]["output_folder"], "wer.txt")
    hparams["model_config"]["save_folder"] = os.path.join(hparams["model_config"]["output_folder"], "save")
    hparams["model_config"]["train_log"] = os.path.join(hparams["model_config"]["output_folder"], "train_log.txt")
    """

    # create exp dir
    sb.create_experiment_directory(
        experiment_directory=config.output_folder,
        hyperparams_to_save=config.exp_config,
        overrides=None
    )

    ### Datasets and Tokenizer ###
    train_data, valid_data, test_data, tokenizer = dataio_prepare(hparams)
    print(len(train_data))
    """
    for x in train_data:
        print(x)
        print(x["sig"].size())
        exit()
    exit()
    """
    train_data = filter_sequences_by_length(train_data, "train")
    valid_data = filter_sequences_by_length(valid_data, "valid")
    test_data  = filter_sequences_by_length(test_data,  "test")

    # run_opts
    run_opts = {"device": "cuda:0"} # certain args from yaml file will autoamtically get picked as run_opts
                                    # see https://github.com/speechbrain/speechbrain/blob/develop/recipes/LibriSpeech/ASR/transformer/train.py#L372
                                    # see https://github.com/speechbrain/speechbrain/blob/d6adc40e742107c34ae38dc63484171938b4d237/speechbrain/core.py#L124

    # load lm model
    #run_on_main(hparams["model_config"]["pretrainer"].collect_files)
    #hparams["model_config"]["pretrainer"].load_collected(device=run_opts["device"])
    #hparams["pretrainer"].load_collected(device=run_opts["device"])

    # Trainer initialization
    #print(type(hparams["model_config"]["modules"]))
    #print(type(hparams))
    #exit()i
    asr_brain = ASR(
        modules=hparams["model_config"]["modules"],
        opt_class=hparams["model_config"]["Adam"],
        hparams=hparams["model_config"],
        run_opts=run_opts,
        checkpointer=hparams["model_config"]["checkpointer"],
    )
    #print(hparams["model_config"]["test_search"])
    #print(hparams["model_config"]["test_search"].lm_modules)
    #hparams["model_config"]["test_search"].lm_modules.load("results/Transformer/2223/save/CKPT+2022-05-14+22-46-15+00/")
    #hparams["model_config"]["test_search"].load(hparams["tokenizer_config"]["sp_model_file"])

    # adding objects to trainer:
    asr_brain.tokenizer = tokenizer # hparams["tokenizer"]

    # Training
    if not config.run_test_only:
        asr_brain.fit(
            asr_brain.hparams.epoch_counter,
            train_data,
            valid_data,
            train_loader_kwargs=hparams["model_config"]["train_dataloader_opts"],
            valid_loader_kwargs=hparams["model_config"]["valid_dataloader_opts"],
        )

    # Testing
    #for k in test_datasets.keys():  # keys are test_clean, test_other etc
    asr_brain.hparams.wer_file = os.path.join(
        config.output_folder, "wer_{}.txt".format("test")
    )
    
    print("RUNNING TEST ON TOP 20 TRAIN")
    asr_brain.evaluate(
        #train_data.filtered_sorted(select_n=20),
        #test_data.filtered_sorted(select_n=2),
        test_data,
        max_key="ACC",
        test_loader_kwargs=hparams["model_config"]["test_dataloader_opts"],
    ) 



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
    parser.add_argument("--seed", type=int, default=8886)

    ## COMBINED ARGS ##
    # this is a bit abusive, various hyperpyyaml configs are kept separate to prevent combinatorial explosion of yaml files
    # this file will be create during runtime by combining all input config files as a step 1
    parser.add_argument("--exp_config", type=str, default="tmp.am_exp_config.yaml", choices=["tmp.am_exp_config.yaml"])
    
    ## OUTPUT ##
    parser.add_argument("--output_folder", type=str, default="transformer", help="final output_folder is 'results/<output_folder>/seed_<seed>_<uuid>'")

    ## CONTROL ##
    parser.add_argument("--run_test_only", action="store_true", help="only run test; typically used by models that are already trained previously")
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
    ##### MAIN #####
    main(config)
