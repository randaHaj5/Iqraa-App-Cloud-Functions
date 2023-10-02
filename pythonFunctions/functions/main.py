from gradio_client import Client
from firebase_admin import initialize_app
import re
import os
import time
import base64
import Levenshtein
import noisereduce as nr
import tempfile
import soundfile as sf
from firebase_functions import https_fn
import librosa
import numpy as np 
import google.cloud.firestore
from firebase_admin import firestore
import sys
from io import StringIO


app = initialize_app()

# method for transcribe audio for tarteel and jonatasgrosman space
def transcribe1(url, filename,api_key):
    # Redirect stdout to a dummy stream
    sys.stdout = StringIO()
    client = Client(url,hf_token=api_key)
    result = client.predict(
            filename,
            api_name="/predict"
        )
    return result


# transcribe audio based on url
def transcribe(url, filename,api_key):
    while True:
        try:
            res=transcribe1(url,filename,api_key)
            break
        except Exception as e:
            print("loading..")
            time.sleep(1)  # Add a short delay before retrying
    return res


# method for assigning api_url
def assignUrl(url):
    if url == "https://tarteel-ai-quicklabeler.hf.space/":
        api_url = "https://elina12-tarteel.hf.space/"
        api_key = "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"

    if url == "https://api-inference.huggingface.co/models/tarteel-ai/whisper-base-ar-quran":
        api_url = "https://elina12-tarteel.hf.space/"
        api_key = "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"
    
    if url == "https://api-inference.huggingface.co/models/jonatasgrosman/wav2vec2-large-xlsr-53-arabic":
        api_url = "https://elina12-asr-arabic.hf.space/"
        api_key="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"

    return api_url,api_key

#base64 to audio
def base64_to_audio_and_export(base64_string):
    try:
        # Decode base64 string to bytes
        decoded_bytes = base64.b64decode(base64_string)
        
        # Create a temporary MP4 file
        temp_mp3_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_mp3_file.write(decoded_bytes)
        temp_mp3_file.close()

        return temp_mp3_file.name

    except Exception as e:
        return str(e)

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
        'صو':'ص',
        'ضا': 'ض',
        'ضو': 'ض',
        'طا': 'ط',
        'طو': 'ط',
        'ظو': 'ظ',
        'عا': 'ع',
        'غا': 'غ',
        'غو': 'غ',
        'فا': 'ف',
        'قا': 'ق',
        'قو': 'ق',
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


def fetch_audio_data(book, page, audio_id):
    collection_name = f"{book}_audio_reference"  # Construct collection name
    # Construct document references
    firestore_client: google.cloud.firestore.Client = firestore.client()
    page_ref = firestore_client.collection(collection_name).document(page)
    audio_ref = page_ref.collection("audios").document(audio_id)
    # Get the audio document snapshot
    audio_snapshot = audio_ref.get()

    # Check if the document exists
    if audio_snapshot.exists:
        # Get the data fields from the snapshot
        audio_data = audio_snapshot.to_dict()

        # Access specific fields
        text= audio_data.get("text")
        url = audio_data.get("url")
        rem = audio_data.get("remove")
        rep = audio_data.get("replace")

        return  text,url,rem, rep
        
    else:
        return None  # Audio document does not exist


# @storage_fn.on_object_finalized(timeout_sec=60, memory=options.MemoryOption.MB_512)   
@https_fn.on_request()
def detectVoice(req: https_fn.Request) -> https_fn.Response:
    try:
        req_data = req.json  # Parse the JSON from the request body
        
        # Check if required parameters exist
        required_params = ["book", "page", "id", "audio"]
        for param in required_params:
            if param not in req_data:
                return https_fn.Response(f'{{"error": "The \'{param}\' parameter is missing"}}', status=400)


        # All required parameters are present
        book = req_data["book"]
        page = req_data["page"]
        id = req_data["id"]
        audio = req_data["audio"]
    
        text, url, rem, rep = fetch_audio_data(book, page, id)
        print("before base64_2_audio")
        audio = base64_to_audio_and_export(audio)
        print("after base64_2_audio")
        audio = denoise_audio(audio)
        print("after denoise_audio")
        word2 = text
        api_url,api_key = assignUrl(url)
        print("before transcribe")
        word1 = transcribe(api_url, audio,api_key)
        print("after transcribe")
        word1, word2 = process(rem, rep, word1, word2)
        print("before compare words")
        similarity = compare_words(word1, word2)
        print("after compare words")
        delete_audio_file(audio)
        return https_fn.Response('{{"similarity": {}}}'.format(similarity))

    except Exception as e:
        error_message = f'{{"error": "An error occurred: {e}"}}'
        return https_fn.Response(error_message, status=500)
