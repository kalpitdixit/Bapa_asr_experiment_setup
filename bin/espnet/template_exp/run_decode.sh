#!/bin/bash

# Copyright 2017 Johns Hopkins University (Shinji Watanabe)
#  Apache 2.0  (http://www.apache.org/licenses/LICENSE-2.0)

. ./path.sh || exit 1;
. ./cmd.sh || exit 1;

# general configuration
backend=pytorch
stage=-1       # start from -1 if you need to start from data download
stop_stage=100
ngpu=0         # number of gpus ("0" uses cpu, otherwise use gpu)
debugmode=1
dumpdir=dump   # directory to dump full features
N=0            # number of minibatches to be used (mainly for debugging). "0" uses all minibatches.
verbose=1      # verbose option
resume=        # Resume the training from snapshot

# feature configuration
do_delta=false

train_config=conf/train_mtlalpha1.0.yaml
lm_config=conf/lm.yaml
decode_config=conf/decode_ctcweight1.0.yaml

# rnnlm related
use_wordlm=true     # false means to train/use a character LM
lm_vocabsize=50000    # effective only for word LMs
lmtag=              # tag for managing LMs
lm_resume=          # specify a snapshot file to resume LM training

# decoding parameter
recog_model=model.loss.best # set a model to be used for decoding: 'model.acc.best' or 'model.loss.best'

# data
datadir=./downloads
an4_root=${datadir}/Bapa
#data_url=http://www.speech.cs.cmu.edu/databases/an4/

# exp tag
tag="" # tag for managing experiments.

. utils/parse_options.sh || exit 1;

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

train_set="train_nodev"
dict=data/lang_1char/${train_set}_units.txt

backend=pytorch

lmtag=$(basename ${lm_config%.*})
lmtag=${lmtag}_word${lm_vocabsize}

lmexpname=train_rnnlm_${backend}_${lmtag}
lmexpdir=exp/${lmexpname}
recog_set="test"
recog_set="inference"

if [ -z ${tag} ]; then
    expname=${train_set}_${backend}_$(basename ${train_config%.*})
    if ${do_delta}; then
        expname=${expname}_delta
    fi
else
    expname=${train_set}_${backend}_${tag}
fi
expdir=exp/${expname}

##### STAGE 0 #####
python local/data_prep.py ${an4_root} ${KALDI_ROOT}/tools/sph2pipe_v2.5/sph2pipe $recog_set

for x in ${recog_set}; do
    for f in text wav.scp utt2spk; do
        sort data/${x}/${f} -o data/${x}/${f}
    done
    utils/utt2spk_to_spk2utt.pl data/${x}/utt2spk > data/${x}/spk2utt
done

##### STAGE 1 #####
fbankdir=fbank
# Generate the fbank features; by default 80-dimensional fbanks with pitch on each frame
for x in inference; do
    steps/make_fbank_pitch.sh --cmd "$train_cmd" --nj 8 --write_utt2num_frames true \
        data/${x} exp/make_fbank/${x} ${fbankdir}
    utils/fix_data_dir.sh data/${x}
done

# compute global CMVN
compute-cmvn-stats scp:data/${train_set}/feats.scp data/${train_set}/cmvn.ark

# dump features
for rtask in ${recog_set}; do
    echo $rtask
    feat_recog_dir=${dumpdir}/${rtask}/delta${do_delta}; mkdir -p ${feat_recog_dir}
    dump.sh --cmd "$train_cmd" --nj 8 --do_delta ${do_delta} \
        data/${rtask}/feats.scp data/${train_set}/cmvn.ark exp/dump_feats/recog/${rtask} \
        ${feat_recog_dir}
done

##### STAGE 2 #####
echo "stage 2: Dictionary and Json Data Preparation"
for rtask in ${recog_set}; do
    feat_recog_dir=${dumpdir}/${rtask}/delta${do_delta}
    data2json.sh --feat ${feat_recog_dir}/feats.scp \
        data/${rtask} ${dict} > ${feat_recog_dir}/data.json
done

##### STAGE 5 #####
echo "stage 5: Decoding"
nj=8

pids=() # initialize pids
for rtask in ${recog_set}; do
(
    decode_dir=decode_${rtask}_$(basename ${decode_config%.*})_${lmtag}
    if [ ${use_wordlm} = true ]; then
        recog_opts="--word-rnnlm ${lmexpdir}/rnnlm.model.best"
    else
        recog_opts="--rnnlm ${lmexpdir}/rnnlm.model.best"
    fi
    feat_recog_dir=${dumpdir}/${rtask}/delta${do_delta}

    # split data
    splitjson.py --parts ${nj} ${feat_recog_dir}/data.json

    #### use GPU for decoding
    ngpu=0
    echo "expdir: $expdir"
    echo "decode_dir: $decode_dir"
    echo "decode_cmd: $decode_cmd"
    ${decode_cmd} JOB=1:${nj} ${expdir}/${decode_dir}/log/decode.JOB.log \
        asr_recog.py \
        --config ${decode_config} \
        --ngpu ${ngpu} \
        --backend ${backend} \
        --debugmode ${debugmode} \
        --verbose ${verbose} \
        --recog-json ${feat_recog_dir}/split${nj}utt/data.JOB.json \
        --result-label ${expdir}/${decode_dir}/data.JOB.json \
        --model ${expdir}/results/${recog_model} \
        ${recog_opts}

    score_sclite.sh ${expdir}/${decode_dir} ${dict}

) &
pids+=($!) # store background pids
done
i=0; for pid in "${pids[@]}"; do wait ${pid} || ((++i)); done
[ ${i} -gt 0 ] && echo "$0: ${i} background jobs are failed." && false
