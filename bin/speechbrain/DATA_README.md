## RAW DATA
Each series of Satsangs comes with:
1. a list of audio files
2. a list of transcripts containing time-segmented transcripts
3. a manually created mapping of audio file to time-segmented transcript file called `audios_sph_transcripts_map.json`

## STEP 1: creating time-segmented audio files
we need time-segmented audio files, and use `create_wav_and_transcript_segments.py` for it. That creates two folders:
1. `segmented-audio-wav` - folder of wav files named with corresponding uuid
   ```
   segmented-audio-wav/3a01be17-speaker1-8fdb4eab.wav
   segmented-audio-wav/3a01be17-speaker1-9025e7e4.wav
   ```
2. `segmented-transcripts` - contains a single file `all.transcriptions`
   ```
   <s> music </s> (3a01be17-speaker1-8fdb4eab)
   <s> music </s> (3a01be17-speaker1-9025e7e4)
   ```
3. `segmented_audios_wav_transcripts_map.json` - each line is a json object mapping a segmented audio, a segmented trancripts 
                                                 and metaaadata
    '''
    {"audio_wav_file": "segmented-audio-wav/3a01be17-speaker1-8fdb4eab.wav", 
     "transcript_all_file": "segmented-transcripts/all.transcriptions",
     "transcript_uid": "3a01be17-speaker1-8fdb4eab",
     "filter_criteria": "Shibir 1,Pravachan 1}
    '''

## Specifying Data to the Modeling Code is done by specifying a list of pairs:
1. `segmented_audios_wav_transcripts_map.json` - str path to json file
2. `filter_criterias` - list of str filter criterias
