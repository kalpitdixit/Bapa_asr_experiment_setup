import os
import sys
import argparse
import logging
import glob
import torch
#from datasets import load_dataset
from hyperpyyaml import load_hyperpyyaml

import speechbrain as sb
from speechbrain.utils.distributed import run_on_main

from utils import get_utterance_manifest_from_datasets, load_hparams, write_hyperpyyaml_file, combine_multiple_hyperpyyaml_files_into_one


logger = logging.getLogger(__name__)


# Define training procedure
class LM(sb.core.Brain):
    def compute_forward(self, batch, stage):
        """Forward computations from the sentence batches to the output probabilities."""
        batch = batch.to(self.device)
        tokens_bos, _ = batch.tokens_bos
        logits = self.hparams.model(tokens_bos)
        pred = self.hparams.log_softmax(logits)
        return pred

    def compute_objectives(self, predictions, batch, stage):
        """Computes the loss given predictions and targets."""
        batch = batch.to(self.device)
        tokens_eos, tokens_len = batch.tokens_eos
        loss = self.hparams.compute_cost(
            predictions, tokens_eos, length=tokens_len
        )
        return loss

    def fit_batch(self, batch):
        """Train the parameters given a single batch in input"""
        predictions = self.compute_forward(batch, sb.Stage.TRAIN)
        loss = self.compute_objectives(predictions, batch, sb.Stage.TRAIN)

        (loss / self.hparams.accu_steps).backward()

        if self.step % self.hparams.accu_steps == 0:
            # gradient clipping & early stop if loss is not fini
            self.check_gradients(loss)

            self.optimizer.step()
            self.optimizer.zero_grad()

            if isinstance(
                self.hparams.lr_annealing, sb.nnet.schedulers.NoamScheduler
            ) or isinstance(
                self.hparams.lr_annealing,
                sb.nnet.schedulers.CyclicCosineScheduler,
            ):
                self.hparams.lr_annealing(self.optimizer)

        return loss

    def on_stage_end(self, stage, stage_loss, epoch):
        """Gets called at the end of a epoch."""
        stage_stats = {"loss": stage_loss}
        if stage == sb.Stage.TRAIN:
            self.train_stats = stage_stats

        if stage == sb.Stage.VALID and sb.utils.distributed.if_main_process():
            if not (
                isinstance(
                    self.hparams.lr_annealing, sb.nnet.schedulers.NoamScheduler
                )
                or isinstance(
                    self.hparams.lr_annealing,
                    sb.nnet.schedulers.CyclicCosineScheduler,
                )
            ):
                old_lr, new_lr = self.hparams.lr_annealing(stage_loss)
                sb.nnet.schedulers.update_learning_rate(self.optimizer, new_lr)
            else:
                old_lr = self.hparams.lr_annealing.current_lr

            self.hparams.train_logger.log_stats(
                stats_meta={"epoch": epoch, "lr": old_lr},
                train_stats=self.train_stats,
                valid_stats=stage_stats,
            )
            self.checkpointer.save_and_keep_only(
                meta=stage_stats, min_keys=["loss"],
            )

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
def dataio_prepare(hparams):
    """grap all the .txt files for transcripts"""
    logging.info("generating datasets...")
    data_folder = hparams["data_folder"]
    train_transcripts = glob.glob(
        os.path.join(data_folder, "train*/**/*.trans.txt"), recursive=True
    )
    dev_transcripts = glob.glob(
        os.path.join(data_folder, "dev*/**/*.trans.txt"), recursive=True
    )
    test_transcripts = glob.glob(
        os.path.join(data_folder, "test*/**/*.trans.txt"), recursive=True
    )

    """prepare data and generate datasets"""
    datasets = load_dataset(
        "dataset.py",
        lm_corpus_path=hparams["lm_corpus_path"],
        data_files={
            "train": train_transcripts,
            "dev": dev_transcripts,
            "test": test_transcripts,
        },
    )

    train_data, valid_data, test_data = (
        datasets["train"],
        datasets["dev"],
        datasets["test"],
    )

    """convert huggingface's dataset to DynamicItemDataset via a magical function"""
    train_data = sb.dataio.dataset.DynamicItemDataset.from_arrow_dataset(
        train_data
    )
    valid_data = sb.dataio.dataset.DynamicItemDataset.from_arrow_dataset(
        valid_data
    )
    test_data = sb.dataio.dataset.DynamicItemDataset.from_arrow_dataset(
        test_data
    )

    datasets = [train_data, valid_data, test_data]

    tokenizer = hparams["tokenizer"]

    """Define text pipeline"""
    # TODO: implement text augmentations pipelines
    @sb.utils.data_pipeline.takes("text")
    @sb.utils.data_pipeline.provides("text", "tokens_bos", "tokens_eos")
    def text_pipeline(text):
        yield text
        tokens_list = tokenizer.encode_as_ids(text)
        tokens_bos = torch.LongTensor([hparams["bos_index"]] + (tokens_list))
        yield tokens_bos
        tokens_eos = torch.LongTensor(tokens_list + [hparams["eos_index"]])
        yield tokens_eos

    sb.dataio.dataset.add_dynamic_item(datasets, text_pipeline)

    # 4. Set output:
    sb.dataio.dataset.set_output_keys(
        datasets, ["id", "text", "tokens_bos", "tokens_eos"],
    )
    return train_data, valid_data, test_data


def main(config):
    ### create Experiment Directory ###
    # combine all hyperparameters into a single file
    hparams = load_hparams(config.exp_config)
    hparams["model_config"] = load_hparams(config.model_config)

    # Create experiment directory
    sb.create_experiment_directory(
        experiment_directory=config.output_folder,
        hyperparams_to_save=config.exp_config,
        overrides=None,
    )

    ### Datasets and Tokenizer ###
    train_data, valid_data, test_data = dataio_prepare(hparams)

    # Trainer initialization
    run_opts = {"device": "cuda:0"} # certain args from yaml file will autoamtically get picked as run_opts

    # We download the tokenizer from HuggingFace (or elsewhere depending on
    # the path given in the YAML file).
    #run_on_main(hparams["pretrainer"].collect_files)
    #hparams["pretrainer"].load_collected(device=run_opts["device"])

    lm_brain = LM(
        modules=hparams["model_config"]["modules"],
        opt_class=hparams["model_config"]["optimizer"],
        hparams=hparams["model_config"],
        run_opts=run_opts,
        checkpointer=hparams["model_config"]["checkpointer"],
    )

    lm_brain.fit(
        lm_brain.hparams.epoch_counter,
        train_data,
        valid_data,
        train_loader_kwargs=hparams["model_config"]["train_dataloader_opts"],
        valid_loader_kwargs=hparams["model_config"]["valid_dataloader_opts"],
    )

    # evaluation
    test_stats = lm_brain.evaluate(
        test_data,
        min_key="loss",
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

    ## COMBINED ARGS ##
    # this is a bit abusive, various hyperpyyaml configs are kept separate to prevent combinatorial explosion of yaml files
    # this file will be create during runtime by combining all input config files as a step 1
    parser.add_argument("--exp_config", type=str, default="tmp.lm_exp_config.yaml", choices=["tmp.lm_exp_config.yaml"])

    ## OUTPUT ##
    parser.add_argument("--output_folder", type=str, required=True)
    return parser.parse_args()



if __name__ == "__main__":
    config = argparser()
    combine_multiple_hyperpyyaml_files_into_one(input_hyperpyyaml_files = {"train_data_config": config.train_data_config,
                                                                           "valid_data_config": config.valid_data_config,
                                                                           "test_data_config" : config.test_data_config,
                                                                           "tokenizer_config" : config.tokenizer_config},
                                                output_hyperpyyaml_file = config.exp_config)

    main(config)

