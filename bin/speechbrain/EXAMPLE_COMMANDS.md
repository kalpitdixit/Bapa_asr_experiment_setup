# TOKENIZER
# tokenizer - small train
python launch_tokenizer_train.py --train_data_config ~/data/data_configs/june_2021/dummy_train.yaml --output_folder tmp_tokenizer  --character_coverage 1.0 --annotation_list_to_check ~/data/data_configs/june_2021/dummy_train.yaml --model_type bpe --vocab_size 500

# ACOUSTIC MODEL (AM)
# acoustic model - small train
python launch_acoustic_model_train.py --train_data_config ~/data/data_configs/june_2021/dummy_train.yaml --valid_data_config ~/data/data_configs/june_2021/dummy_val.yaml --test_data_config ~/data/data_configs/june_2021/dummy_test.yaml --output_folder tmp_am  --tokenizer_config tmp_tokenizer/sp_vocab_500_bpe.yaml --model_config acoustic_model_configs/transformer.yaml

# LANGUAGE MODEL (LM)
# language model - small train
python launch_language_model_train.py  --output_folder tmp_lm --train_data_config ~/data/data_configs/june_2021/dummy_train.yaml --valid_data_config ~/data/data_configs/june_2021/dummy_val.yaml --test_data_config ~/data/data_configs/june_2021/dummy_test.yaml --tokenizer_config tmp_tokenizer/sp_vocab_500_bpe.yaml --model_config language_model_configs/transformer_dummy.yaml
