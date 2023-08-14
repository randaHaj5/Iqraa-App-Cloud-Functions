from gradio_client import Client
from firebase_admin import initialize_app
import re
import os
import time
import base64
import Levenshtein
import noisereduce as nr
import uuid
import soundfile as sf
from firebase_functions import https_fn
import librosa
import numpy as np

app = initialize_app()


# method for transcribe audio for tarteel and jonatasgrosman space
def transcribe1(url,filename):
    client = Client(url)
    result = client.predict(
        # str (filepath or URL to file) in 'Input' Audio component
        filename,
        api_name="/predict"
    )
    return result


# transcribe audio based on url
def transcribe(url, filename):
    while True:
        try:
            res=transcribe1(url,filename)
            break
        except Exception as e:
            time.sleep(1)  # Add a short delay before retrying
        return res


# method for assigning api_url
def assignUrl(url):
    if url == "https://tarteel-ai-quicklabeler.hf.space/":
        api_url = "https://elina12-tarteel.hf.space/"

    if url == "https://api-inference.huggingface.co/models/tarteel-ai/whisper-base-ar-quran":
        api_url = "https://elina12-tarteel.hf.space/"

    if url == "https://api-inference.huggingface.co/models/jonatasgrosman/wav2vec2-large-xlsr-53-arabic":
        api_url = "https://elina12-asr-arabic.hf.space/"

    return api_url

# base64 to wav
def save_audio_from_base64(encoded_audio_base64):
    # Decode the base64 string to bytes
    audio_bytes = base64.b64decode(encoded_audio_base64)

    # Generate a unique filename for the audio
    unique_id = str(uuid.uuid4())[:8]
    output_file = f'audio_{unique_id}.wav'

    # Save the audio to the new file
    sf.write(output_file, audio_bytes, 16000)

    # Return the filename of the saved audio
    return output_file

# denoise the audio
def denoise_audio(audio_file):
    # Load the audio file using the provided audio_id
    audio, sr = librosa.load(audio_file, sr=16000)
    if len(audio.shape) > 1 and audio.shape[1] > 1:
        audio = np.mean(audio, axis=1)
    else:
        audio = audio.squeeze()

    # Reduce noise with adjusted parameters
    win_length = 512  # Window length for STFT (in samples)
    hop_length = 256  # Hop size for STFT (in samples)
    reduced_noise = nr.reduce_noise(
        y=audio, sr=sr, win_length=win_length, hop_length=hop_length, prop_decrease=0.4)

    # Save the denoised audio to the original file
    sf.write(audio_file, reduced_noise, sr)

    # Return the filename of the denoised audio
    return audio_file


def remove_arabic_diacritics(text):
    # Define the vowels to remove
    vowels_to_remove = ['َ', 'ُ', 'ٌ', 'ِ', 'ٍ', 'ْ',
                        '-', '_', ' ', 'ى', '!', '.', '?', '؟', 'ّ', "ً"]

    # Remove diacritics (vowels) from Arabic text
    for vowel in vowels_to_remove:
        text = text.replace(vowel, '')
    return text


def replace_letter_combinations(text):
    # Define the letter combinations to replace
    combinations_to_replace = {
        'ً': 'ن',
        'اً': 'ن',
        'با': 'ب',
        'تا': 'ت',
        'ثا': 'ث',
        'جا': 'ج',
        'حا': 'ح',
        'خا': 'خ',
        'دا': 'د',
        'ذا': 'ذ',
        'را': 'ر',
        'زا': 'ز',
        'سا': 'س',
        'شا': 'ش',
        'صا': 'ص',
        'ضا': 'ض',
        'طا': 'ط',
        'ظا': 'ظ',
        'عا': 'ع',
        'غا': 'غ',
        'فا': 'ف',
        'قا': 'ق',
        'كا': 'ك',
        'لا': 'ل',
        'ما': 'م',
        'نا': 'ن',
        'ها': 'ه',
        'وا': 'و',
        'يا': 'ي',
        'آه': 'أ',
        'أا': 'أ',
        'آا': 'أ',
        'آ': 'أ',
        'ءا': 'أ',
        'ء': 'أ'
        # Add more combinations as needed
    }
    # Replace the letter combinations in the text
    for combination, replacement in combinations_to_replace.items():
        text = re.sub(combination, replacement, text)

    return text


def process(rem, rep, w1, w2):
    if rem == "yes":
        w1 = remove_arabic_diacritics(w1)
        w2 = remove_arabic_diacritics(w2)
    if rep == "yes":
        w1 = replace_letter_combinations(w1)
        w2 = replace_letter_combinations(w2)

    return w1, w2

#compare the words
def compare_words(word1, word2):
    # Remove spaces from the words
    word1 = word1.replace(" ", "")
    word2 = word2.replace(" ", "")
    # Calculate the Levenshtein distance between the words
    distance = Levenshtein.distance(word1, word2)
    return "true" if distance == 0 else "false"


def delete_audio_file(input_file):
    # delete the denoised audio file to clean up
    if os.path.exists(input_file):
        os.remove(input_file)


@https_fn.on_request()
def similarity(req: https_fn.Request) -> https_fn.Response:
    text = req.args.get("text")
    url = req.args.get("url")
    remove = req.args.get("remove")
    replace = req.args.get("replace")
    audio = req.args.get("audio")
    audio = save_audio_from_base64(audio)
    audio = denoise_audio(audio)

    word2 = text
    api_url = assignUrl(url)
    word1 = transcribe(api_url, audio)
    word1, word2 = process(remove, replace, word1, word2)
    similarity = compare_words(word1, word2)
    delete_audio_file(audio)

    return https_fn.Response(similarity)