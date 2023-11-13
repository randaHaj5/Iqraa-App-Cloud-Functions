from collections import defaultdict
from transformers import pipeline
import gradio as gr
import json
import os
from pydub import AudioSegment
from pydub.playback import play

# pipe = pipeline(model="jonatasgrosman/wav2vec2-large-xlsr-53-arabic")

# def transcribe(audio):
#     text = pipe(audio)["text"]
#     return text

# iface = gr.Interface(
#     fn=transcribe,
#     inputs=gr.Audio(source="upload", type="filepath"),
#     outputs="text",

# )
def getModel(url):
    if url == "https://tarteel-ai-quicklabeler.hf.space/":
        model = "tarteel-ai/whisper-base-ar-quran"

    if url == "https://api-inference.huggingface.co/models/tarteel-ai/whisper-base-ar-quran":
        model = "tarteel-ai/whisper-base-ar-quran"

    if url == "https://api-inference.huggingface.co/models/jonatasgrosman/wav2vec2-large-xlsr-53-arabic":
        model = "jonatasgrosman/wav2vec2-large-xlsr-53-arabic"

    if model is None:
        raise Exception("model not found")
    return model


def fetch_data_from_json(book,page, audio):
    # open the json file
    with open(f'/Users/slomax/Dev/Navybits/AI/Iqraa-App-Cloud-Functions/pythonFunctions/functions/Refs/${book}Refs.json') as json_file:
        data = json.load(json_file)
        # get page object then get the audio object
        # print(data[page][audio])
        return data[page][audio]["text"], data[page][audio]["url"]


def check_prediction(text, prediction):
    # add here future replacement of chars and shit

    return text == prediction



if __name__ == "__main__":
    # make new fetch from json function to get the data
    # then send the downloaded audios to the hugging spaces.(maybe should infrece locally for a faster result?)
    # print(fetch_audio_data('book3','p1','a0005'))
    # print(tarteel("/Users/slomax/Dev/Navybits/AI/Iqraa-App-Cloud-Functions/pythonFunctions/functions/a0002.mp3"))
    # create an empty json file then load it
    sound = AudioSegment.from_mp3('/Users/slomax/Dev/Navybits/AI/Iqraa-App-Cloud-Functions/pythonFunctions/functions/a.mp3')
    play(sound)

    match,mismatch = 0,0
    results = defaultdict(lambda: defaultdict(dict))
    json_file_path = 'results.json'
    sorted_json_file_path = 'sorted_results.json'
    try:
        with open(json_file_path, 'r') as json_file:
            results = json.load(json_file)
    except FileNotFoundError:
        results = defaultdict(lambda: defaultdict(dict))
    # loop on sample folder and sub folders
    for bigroot, bigdirs, files in os.walk(
            "/Users/slomax/Dev/Navybits/AI/Iqraa-App-Cloud-Functions/pythonFunctions/functions/sample"):
        for dir in bigdirs:
            print(f'dir: {dir}')
            print(os.path.join(bigroot, dir))
            for root, dirs, files in os.walk(os.path.join(bigroot, dir)):
                print(f'root: {root}, dirs: {dirs}')
                for file in files:
                    path = os.path.join(root, file)
                    page = os.path.basename(os.path.dirname(path))
                    file = os.path.basename(path)
                    audio = os.path.splitext(file)[0]
                    print('audio', audio)
                    if file.endswith(".mp3"):
                        text, url = fetch_data_from_json(page, audio)
                        # get the model from the url
                        model = getModel(url)
                        # predict the text from the audio file
                        pipe = pipeline(model=model)
                        prediction = pipe(os.path.join(root, file))["text"]
                        print(prediction)
                        # check if the prediction is correct
                        isMatch = check_prediction(text, prediction)
                        # save the results in the json file in their corresponding page
                        results[page][audio]["model"] = model
                        results[page][audio]["text"] = text
                        results[page][audio]["prediction"] = prediction
                        results[page][audio]["matched"] = isMatch

                        match, mismatch = (match + 1, mismatch) if isMatch else (match, mismatch + 1)

                        with open(json_file_path, 'w', encoding='utf-8') as json_file:
                            json.dump(results, json_file, ensure_ascii=False, indent=4)

    sorted_res = {page: {audio_name: info for audio_name, info in sorted(audios.items())} for page, audios in
                  sorted(results.items())}
    with open(sorted_json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(sorted_res, json_file, ensure_ascii=False, indent=4)
    # multiline print
    percentage = match / (mismatch + match) * 100
    print(f"""
        match: {match},
        mismatch: {mismatch},
      =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
        percentage: {percentage},
      =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
    """)
    play(sound)

