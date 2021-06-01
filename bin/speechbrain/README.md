# SETUP
## Install SeepchBrain
`git clone https://github.com/speechbrain/speechbrain.git`  
Commit ID: 9382406e8e8b42753ac317bf5b2ef1a91ddfa9c3

## Standard ASR Process
see [this](https://github.com/speechbrain/speechbrain/tree/develop/recipes/LibriSpeech) for the need to train Tokenizer first and only then AM and LM.

# DESIGN PRINCIPLES
1. we use [HyperPyYAML](`https://github.com/speechbrain/HyperPyYAML#yaml-basics`) for all kinds of hyperparam communication


1. datasets are communicated between data-store/cli and speechbrain interface by compiling manifest files of individual utterances; jsonl
