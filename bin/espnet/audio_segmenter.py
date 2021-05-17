import io
import os
import math
import subprocess
import sys
import re
from os import listdir
from os.path import isfile, join
from multiprocessing.dummy import Pool
from optparse import OptionParser
import errno
from subprocess import check_call, PIPE, Popen
import shlex
from auditok import ADSFactory, AudioEnergyValidator, StreamTokenizer

from google.cloud import speech_v1p1beta1 as speech
from google.cloud.client import Client
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types
from google.cloud.speech_v1p1beta1.proto.cloud_speech_pb2 import SpeechContext
import argparse
from tqdm import tqdm


def changeMP3PlaybackSpeed(fileFullPathname, playbackspeed):
    # Get the file name withoutextension
    file_name = os.path.basename(fileFullPathname)
    raw_file_name = os.path.basename(file_name).split('.')[0]
    file_dir = os.path.dirname(fileFullPathname)
    print('playbackspeed - {}'.format(playbackspeed.replace('.', '')))
    file_path_output = file_dir + '\\' + raw_file_name+'_PBS'+playbackspeed.replace('.', '') + '.mp3'
    print('processing file: %s' % fileFullPathname)
    print('"atempo={}"'.format(playbackspeed))
    subprocess.call(
        ['ffmpeg', '-i', fileFullPathname, '-filter:a', 'atempo={}'.format(playbackspeed), '-vn', file_path_output], shell=True)
    print('file %s saved' % file_path_output)
    return file_path_output


# In[3]:


def convertMP3toWav(fileFullPathname, bitrate):
    # Get the file name withoutextension
    file_name = os.path.basename(fileFullPathname)
    raw_file_name = os.path.basename(file_name).split('.')[0]
    file_dir = os.path.dirname(fileFullPathname)
    file_path_output = file_dir + '\output\\' + raw_file_name+'_'+bitrate + '.wav'
    #print('processing file: %s' % fileFullPathname)
    subprocess.call(
        ['ffmpeg', '-i', fileFullPathname, '-codec:a', 'pcm_s16le', '-ac', '1', '-ar', bitrate, file_path_output], shell=True)
    #print('file %s saved' % file_path_output)
    return file_path_output


# In[4]:


def convertMP3toFlac(fileFullPathname, bitrate):
    # Get the file name withoutextension
    file_name = os.path.basename(fileFullPathname)
    raw_file_name = os.path.basename(file_name).split('.')[0]
    file_dir = os.path.dirname(fileFullPathname)
    file_path_output = file_dir + '\output\\' + raw_file_name+'_'+bitrate + '.flac'
    print('processing file: %s' % fileFullPathname)
    subprocess.call(
        ['ffmpeg', '-i', fileFullPathname, '-ac', '1', '-ar', bitrate, file_path_output], shell=True)
    print('file %s saved' % file_path_output)
    return file_path_output


# In[5]:


def get_duration(file):
    process = subprocess.Popen(['ffmpeg',  '-i', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = process.communicate()
    length_regexp = b'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})+,'
    re_length = re.compile(length_regexp)
    matches = re_length.search(stdout)
    #print(stdout)
    if matches:
        video_length = int(matches.group(1)) * 3600 +                        int(matches.group(2)) * 60 +                        int(matches.group(3)) +                        int(matches.group(4))/100
        #print("Video length in seconds: {} --- {} {} {} {}".format(video_length, int(matches.group(1)), int(matches.group(2)),int(matches.group(3)), int(matches.group(4))))
    else:
        #print("Can't determine video length.")
        raise SystemExit
    # return round(float(output))  # ugly, but rounds your seconds up or down
    return float(video_length)


# In[6]:


def SplitWavFileIntoSeconds(filename, split_length_inSeconds):

    length_regexp = 'Duration: (\d{2}):(\d{2}):(\d{2})\.\d+,'
    re_length = re.compile(length_regexp)

    if split_length_inSeconds <= 0:
        print("Split length can't be 0")
        raise SystemExit
    #print("File to be split {}".format(filename))
    
    video_length = get_duration(filename)
    split_count = math.ceil(video_length / split_length_inSeconds)

    if split_count == 1:
        print("Video length is less than the target split length.")
        raise SystemExit

    # Get the file name withoutextension
    raw_file_name = os.path.basename(filename).split('.')[0]
    file_dir = os.path.dirname(filename) + '\\'+ raw_file_name

    try:
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    change_file_name = file_dir + '\\'
    
    for n in range(split_count):
        split_start = split_length_inSeconds * n
        pth, ext = filename.rsplit(".", 1)
        cmd = "ffmpeg -i \"{}\" -vcodec copy  -strict -2 -ss {} -t {} \"{}{}.{}\"".            format(filename, split_start, split_length_inSeconds, change_file_name, n, ext)
        #print("About to run: {}".format(cmd))
        check_call(shlex.split(cmd), universal_newlines=True)
    return change_file_name + "\\"


# In[7]:


def SplitWavFileIntoSeconds_GoingBack(filename, split_length_inSeconds, silence_Period, file_period_dic):
    length_regexp = 'Duration: (\d{2}):(\d{2}):(\d{2})\.\d+,'
    re_length = re.compile(length_regexp)

    if split_length_inSeconds <= 0 | split_length_inSeconds >= 60:
        print("Split length can't be 0")
        raise SystemExit
    print("File to be split {}".format(filename))
    
    # Get the file name withoutextension
    raw_file_name = os.path.basename(filename).split('.')[0]
    file_dir = os.path.dirname(filename) + '\\'+ raw_file_name

    try:
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    change_file_name = file_dir + '\\'
    split_end = 0
    split_start = 0
    i = 0
    tokens = getSplitAudioDurationListBetweenSilence(filename,split_length_inSeconds,silence_Period)
    for j, t in tqdm(enumerate(tokens)):
        split_start = t[1]/100
        if (split_start < 1):
            split_start = 0
        else:
            split_start = split_end - 1
        split_end = (t[2]/100) + 1
        pth, ext = filename.rsplit(".", 1)
        if (split_end-split_start >= 60):
            newSplitFile1Start = split_start - 1
            newSplitFile1End = split_end - 50
            newSplitFile2Start = newSplitFile1End - 1
            newSplitFile2End = split_end + 1
            cmd = "ffmpeg -i \"{}\" -ss {} -to {} -c:a copy \"{}{}.{}\"".            format(filename, newSplitFile1Start, newSplitFile1End, change_file_name, i, ext)
            #print("About to run: {}".format(cmd))
            check_call(shlex.split(cmd), universal_newlines=True)
            file_period_dic.update({i:[newSplitFile1Start+1,newSplitFile1End]})
            i = i + 1
            cmd = "ffmpeg -i \"{}\" -ss {} -to {} -c:a copy \"{}{}.{}\"".            format(filename, newSplitFile2Start, newSplitFile2End, change_file_name, i, ext)
            #print("About to run: {}".format(cmd))
            check_call(shlex.split(cmd), universal_newlines=True)
            file_period_dic.update({i:[newSplitFile2Start+1,newSplitFile2End-1]})
            i = i + 1
        else:
            cmd = "ffmpeg -i \"{}\" -ss {} -to {} -c:a copy \"{}{}.{}\"".                format(filename, split_start, split_end, change_file_name, i, ext)
            #print("About to run: {}".format(cmd))
            check_call(shlex.split(cmd), universal_newlines=True)
            if (split_start == 0):
                file_period_dic.update({i:[split_start,split_end-1]})
            else:
                file_period_dic.update({i:[split_start+1,split_end-1]})
            i = i + 1
    #print(file_period_dic)
    return change_file_name


# In[8]:


def SplitFlacFileIntoSeconds_GoingBack(filename, split_length_inSeconds):

    length_regexp = 'Duration: (\d{2}):(\d{2}):(\d{2})\.\d+,'
    re_length = re.compile(length_regexp)

    if split_length_inSeconds <= 0 | split_length_inSeconds >= 60:
        print("Split length can't be 0")
        raise SystemExit
    #print("File to be split {}".format(filename))
    
    video_length = get_duration(filename)
    split_count = math.ceil(video_length / split_length_inSeconds)

    if split_count == 1:
        print("Video length is less than the target split length.")
        raise SystemExit

    # Get the file name withoutextension
    raw_file_name = os.path.basename(filename).split('.')[0]
    file_dir = os.path.dirname(filename) + '\\'+ raw_file_name

    try:
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    change_file_name = file_dir + '\\'
    split_end = 0
    split_start = 0
    for n in range(split_count):
        if (split_start > 0):
            split_start = split_end - 10
        split_end = split_start + split_length_inSeconds
        pth, ext = filename.rsplit(".", 1)
        cmd = "ffmpeg -i \"{}\" -vcodec copy -strict -2 -ss {} -t {} \"{}{}.{}\"".            format(filename, split_start, split_length_inSeconds, change_file_name, n, ext)
        #print("About to run: {}".format(cmd))
        check_call(shlex.split(cmd), universal_newlines=True)
        split_start = split_end
    return change_file_name


# In[9]:


def getSplitAudioDurationListBetweenSilence(fileName,eachAudioLen,silencePeriod,energyThreshold=55):
    try:
        # We set the `record` argument to True so that we can rewind the source
        asource = ADSFactory.ads(filename=fileName, record=False)

        validator = AudioEnergyValidator(sample_width=asource.get_sample_width(), energy_threshold=energyThreshold)

        # Default analysis window is 10 ms (float(asource.get_block_size()) / asource.get_sampling_rate())
        # min_length=20 : minimum length of a valid audio activity is 20 * 10 == 200 ms
        # max_length=400 :  maximum length of a valid audio activity is 400 * 10 == 4000 ms == 4 seconds
        # max_continuous_silence=30 : maximum length of a tolerated  silence within a valid audio activity is 30 * 30 == 300 ms 
        tokenizer = StreamTokenizer(validator=validator, min_length=400, max_length=eachAudioLen*100, max_continuous_silence=silencePeriod*100)

        asource.open()
        tokens = tokenizer.tokenize(asource)

        # Play detected regions back
        #player = player_for(asource)

        # Rewind and read the whole signal
        #asource.rewind()
        #original_signal = []

        #while True:
        #    w = asource.read()
        #    if w is None:
        #        break
        #    original_signal.append(w)


        #original_signal = b''.join(original_signal)
        #player.play(original_signal)

        #print("\n ** playing detected regions...\n")
        #for i,t in enumerate(tokens):
        #    print("Token [{0}] starts at {1} and ends at {2}".format(i+1, t[1], t[2]))
            #data = b''.join(t[0])
            #player.play(data)

        #assert len(tokens) == 8

        asource.close()
        #player.stop()
    except KeyboardInterrupt:

        #player.stop()
        asource.close()
        #sys.exit(0)

    except Exception as e:

        sys.stderr.write(str(e) + "\n")
        #sys.exit(1)
    return tokens


# In[10]:


def getint(name):
    num, _ = name.split('.')
    return int(num)


# In[11]:


def sorted_nicely( l ):
    """ Sorts the given iterable in the way that is expected.
 
    Required arguments:
    l -- The iterable to be sorted.
 
    """
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key['idx'])]
    return sorted(l, key = alphanum_key)


# In[12]:


def convertWAVToTranscript(fileFullPathname, split_length_inSeconds):
    pool = Pool(8) # Number of concurrent threads

    #spk = new SpeechContext { phrases : [ "લગભગ", "માત્ર","શ્રી ત્રંબકભાઈ","સોભાગભાઈ","દેહ વિલય","જ્ઞાની પુરુષ","દશા","રુવાડા","ઐશ્વર્ય","એ","જ્ઞાન","વિકલ્પ","ત્યારે","હમણાં","મુમુક્ષુ","દશા","માર્ગ","અદ્દભુત","નિશ્ચય","સ્મૃતિ" ] };
    config = types.RecognitionConfig(
    encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
    #sample_rate_hertz=512000,
    language_code='gu-IN',
    speechContexts = {"phrases" : ['લગભગ', 'માત્ર','શ્રી ત્રંબકભાઈ','સોભાગભાઈ','દેહ વિલય','જ્ઞાની પુરુષ','દશા','રુવાડા','ઐશ્વર્ય','એ','જ્ઞાન','વિકલ્પ','ત્યારે','હમણાં']} #,'મુમુક્ષુ','દશા','માર્ગ','અદ્દભુત','નિશ્ચય','સ્મૃતિ'])] 
        #,"મુમુક્ષુ","દશા","માર્ગ","અદ્દભુત","નિશ્ચય","સ્મૃતિ" ])]
    )
    files = [f for f in listdir(fileFullPathname) if isfile(join(fileFullPathname, f))]   
    #file_Direcotry = os.path.dirname(fileFullPathname)
    
    def transcribe(data):
        idx, file = data
        num, _ = file.split('.')
        text_script = ""
        name = file
        #print(file + " - started")
        # Loads the audio into memory
        with io.open(fileFullPathname+'\\'+file, 'rb') as audio_file:
            content = audio_file.read()
            audio = types.RecognitionAudio(content=content)
        # Transcribe audio file
        # Detects speech in the audio file
        client = speech.SpeechClient()
        response = client.recognize(config, audio)
        for result in response.results:
            text_script += result.alternatives[0].transcript
            
        #print(name + " - done")
        return {
            "idx": num,
            "text": text_script
        }

    all_text = pool.map(transcribe, enumerate(files))
    pool.close()
    pool.join()

    transcript = ""
    total_seconds = 0
    for t in sorted_nicely(all_text): #sorted(all_text, key=lambda x: sorted_nicely(x['idx'])):
        #total_seconds += split_length_inSeconds
        print("Duration of file {} is {}".format(fileFullPathname+t['idx']+'.wav', math.ceil(get_duration(fileFullPathname+'\\'+t['idx']+'.wav'))))
        total_seconds += math.ceil(get_duration(fileFullPathname+t['idx']+'.wav'))
        # Cool shortcut from:
        # https://stackoverflow.com/questions/775049/python-time-seconds-to-hms
        # to get hours, minutes and seconds
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)

        # Format time as h:m:s - 30 seconds of text
        transcript = transcript + "{:0>2d}:{:0>2d}:{:0>2d} {}\n".format(h, m, s, t['text'])

    #print(transcript)

    with open("transcript.txt", "w", encoding='utf-8') as f:
        f.write(transcript)


def convertWAVToTranscript_v1(fileFullPathname, split_length_inSeconds, file_period_dic):
    #print("inside convertWAVToTranscript_v1 - {0}".format(file_period_dic))
    pool = Pool(32) # Number of concurrent threads

    encoding = enums.RecognitionConfig.AudioEncoding.LINEAR16
    language_code='gu-IN'
    #spk = new SpeechContext { phrases : [ "લગભગ", "માત્ર","શ્રી ત્રંબકભાઈ","સોભાગભાઈ","દેહ વિલય","જ્ઞાની પુરુષ","દશા","રુવાડા","ઐશ્વર્ય","એ","જ્ઞાન","વિકલ્પ","ત્યારે","હમણાં","મુમુક્ષુ","દશા","માર્ગ","અદ્દભુત","નિશ્ચય","સ્મૃતિ" ] };
    HINTS = ['લગભગ', 'માત્ર','શ્રી ત્રંબકભાઈ','સોભાગ','ભાઈ','દેહ વિલય','જ્ઞાની પુરુષ','દશા','રુવાડા','ઐશ્વર્ય','એ','જ્ઞાન','વિકલ્પ','ત્યારે','હમણાં'] #,'મુમુક્ષુ','દશા','માર્ગ','અદ્દભુત','નિશ્ચય','સ્મૃતિ'])] 
    
    files = [f for f in listdir(fileFullPathname) if isfile(join(fileFullPathname, f))] 
    config = speech.types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        #sample_rate_hertz=512000,
        language_code='gu-IN',
        use_enhanced=True,
        model='default',
        enable_automatic_punctuation=True,
        #enable_word_time_offsets=True,
        audio_channel_count=1,
        alternative_language_codes=['en-IN'],
        speech_contexts=[speech.types.SpeechContext(
            phrases=['લગભગ', 'માત્ર','શ્રી ત્રંબકભાઈ','સોભાગ','ભાઈ','દેહ વિલય','જ્ઞાની પુરુષ','દશા','રુવાડા','ઐશ્વર્ય','એ','જ્ઞાન','વિકલ્પ','ત્યારે','હમણાં','મુમુક્ષુ','દશા','માર્ગ','અદ્દભુત','નિશ્ચય','સ્મૃતિ'])]
        )

    def transcribe(data):
        idx, file = data
        num, _ = file.split('.')
        text_script = ""
        name = file
        #print(file + " - started")
        audioLengthInSeconds = math.ceil(get_duration(fileFullPathname+'\\'+file))
        
        if (audioLengthInSeconds <= 59):
            # Loads the audio into memory
            with io.open(fileFullPathname+'\\'+file, 'rb') as audio_file:
                content = audio_file.read()
                audio = speech.types.RecognitionAudio(content=content)
            # Transcribe audio file
            # Detects speech in the audio file
            client = speech.SpeechClient()
            response = client.recognize(config, audio)
            for result in response.results:
                text_script += result.alternatives[0].transcript  
            
        #print(name + " - done")
        return {
            "idx": num,
            "text": text_script
        }

    all_text = pool.map(transcribe, enumerate(files))
    pool.close()
    pool.join()

    transcript = ""
    total_seconds = 0
    MAXAPPENDPARAGRAPH = 14
    appendParagraphCount = -1
    appendParagraphText = ""
    for t in sorted_nicely(all_text): 
        str_total_seconds, end_total_seconds = file_period_dic[int(t['idx'])]
        end_m, end_s = divmod(end_total_seconds, 60)
        end_h, end_m = divmod(end_m, 60)
        appendParagraphCount = appendParagraphCount + 1
        if (appendParagraphCount == 0):
            str_m, str_s = divmod(str_total_seconds, 60)
            str_h, str_m = divmod(str_m, 60)
            appendParagraphText =  t['text'] + " "
        elif (appendParagraphCount == MAXAPPENDPARAGRAPH):
            appendParagraphText =  appendParagraphText + t['text']
            # Format time as h:m:s - 30 seconds of text
            transcript = transcript + "{:0>2d}:{:0>2d}:{:0>2d} - {:0>2d}:{:0>2d}:{:0>2d} {}\n".format(int(str_h), int(str_m), int(str_s), int(end_h), int(end_m), int(end_s), appendParagraphText)
            appendParagraphCount = -1
            appendParagraphText = ""
        else:
            appendParagraphText =  appendParagraphText + t['text'] + " "
    
    if (appendParagraphCount >= 0 and appendParagraphCount <= (MAXAPPENDPARAGRAPH-1)):
        transcript = transcript + "{:0>2d}:{:0>2d}:{:0>2d} - {:0>2d}:{:0>2d}:{:0>2d} {}\n".format(int(str_h), int(str_m), int(str_s), int(end_h), int(end_m), int(end_s), appendParagraphText)

    #print(transcript)
    fileName = os.path.basename(os.path.normpath(fileFullPathname))
    with open("{}.txt".format(fileName), "w", encoding='utf-8') as f:
        f.write(transcript)


def convertFLACToTranscript(fileFullPathname, split_length_inSeconds):
    pool = Pool(16) # Number of concurrent threads

    config = types.RecognitionConfig(
    encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
    #sample_rate_hertz=512000,
    language_code='gu-IN')
    files = [f for f in listdir(fileFullPathname) if isfile(join(fileFullPathname, f))]   
    #file_Direcotry = os.path.dirname(fileFullPathname)
    
    def transcribe(data):
        idx, file = data
        num, _ = file.split('.')
        text_script = ""
        name = file
        print(file + " - started")
        # Loads the audio into memory
        with io.open(fileFullPathname+'\\'+file, 'rb') as audio_file:
            content = audio_file.read()
            audio = types.RecognitionAudio(content=content)
        # Transcribe audio file
        # Detects speech in the audio file
        client = speech.SpeechClient()
        response = client.recognize(config, audio)
        for result in response.results:
            text_script += result.alternatives[0].transcript
            
        print(name + " - done")
        return {
            "idx": num,
            "text": text_script
        }

    all_text = pool.map(transcribe, enumerate(files))
    pool.close()
    pool.join()

    transcript = ""
    total_seconds = 0
    for t in sorted_nicely(all_text): #sorted(all_text, key=lambda x: sorted_nicely(x['idx'])):
        #print("Duration of file {} is {}".format(fileFullPathname+t['idx']+'.flac', math.ceil(get_duration(fileFullPathname+'\\'+t['idx']+'.flac'))))
        total_seconds += math.ceil(get_duration(fileFullPathname+t['idx']+'.flac'))
        # Cool shortcut from:
        # https://stackoverflow.com/questions/775049/python-time-seconds-to-hms
        # to get hours, minutes and seconds
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)

        # Format time as h:m:s - 30 seconds of text
        transcript = transcript + "{:0>2d}:{:0>2d}:{:0>2d} {}\n".format(h, m, s, t['text'])

    #print(transcript)

    with open("transcript.txt", "w", encoding='utf-8') as f:
        f.write(transcript)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # This is the correct way to handle accepting multiple arguments.
    # '+' == 1 or more.
    # '*' == 0 or more.
    # '?' == 0 or 1.
    # An int is an explicit number of arguments to accept.
    parser.add_argument('-n', '--nargs', nargs='+', dest='fileList', default=[])
    #fileOutputPath = changeMP3PlaybackSpeed(
    #        r'C:\Users\tejas magia\OneDrive\Documents\Personal\DataScience\DataScience\SpeechRecognition\Test\audio\20417182271.mp3'
    #        ,'1')
    results = parser.parse_args()
    directoryPath = r'F:\Speechrecog\audio'
    #fileList = ['20020311_1 - Copy.mp3','20020311_1 - Copy.mp3','20020311_1 - Copy.mp3','20020311_1 - Copy.mp3']
    split_length_inSeconds = 56
    rewindAudio = 0.5
    audioBitRateInKbps = '46000'
    for file in tqdm(results.fileList):
        filePath = '{0}\{1}'.format(directoryPath,file)
        print(filePath)
        file_period_dic = {}
        SplitfileOutputPath = SplitWavFileIntoSeconds_GoingBack(convertMP3toWav(filePath, audioBitRateInKbps),split_length_inSeconds,rewindAudio, file_period_dic)
        #print("main caller {0}".format(file_period_dic))
        convertWAVToTranscript_v1(SplitfileOutputPath,split_length_inSeconds,file_period_dic)

