# URGENT
- use lm in `test_search` in `acoustic_model_configs/transformer.yaml`; see the librispeech yaml file for reference if needed
- can re-increase the `test_beam_size` back to 66 from the current 10 (which is the same as the `val_beam_size`)

# Data
- remove the segments with only "music" as the transcript, it maybe causing the empty outputs
- see this link for limiting audio span in seconds for memory: https://github.com/speechbrain/speechbrain/issues/764

# Machine Learning
- consider using bos/eos

