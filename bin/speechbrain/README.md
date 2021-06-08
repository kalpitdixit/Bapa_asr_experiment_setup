# SETUP
* install specific library versions from `requirements.txt`

## Standard ASR Process
see [this (LibriSpeech recipe)](https://github.com/speechbrain/speechbrain/tree/develop/recipes/LibriSpeech) for the need to train Tokenizer first and only then AM and LM.

# Design Principles
1. we use [HyperPyYAML](`https://github.com/speechbrain/HyperPyYAML#yaml-basics`) for all hyperparameter communication


