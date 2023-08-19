from directional_cnns import feature_extraction
from pathlib import Path
import joblib
from os.path import join
from multiprocessing import Pool
import warnings

from directional_cnns.groundtruth import TempoGroundTruth

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
import os

# only_in_ground_truth=["annotations/key_train.tsv", "annotations/key_valid.tsv"]
only_in_ground_truth=[]

ground_truths = list(map(lambda x:TempoGroundTruth(x), only_in_ground_truth))

def get_files(root_dir,extensions):
    all_files = []
    for ext in extensions:
        all_files.extend(Path(root_dir).rglob(ext))
    return all_files

def lookup_audio_files(audio_folder):
    all_audio_files = get_files(audio_folder,["*.mp3","*.wav"])
    def in_ground_truths(file:Path):
        for g in ground_truths:
            key = file.name.replace('.LOFI.mp3', '').replace('.mp3', '').replace('.wav', '')
            if key in g.labels:
                return True
        return False
    if len(ground_truths) != 0:
        all_audio_files = filter(in_ground_truths,all_audio_files)
    all_audio_files = list(map(lambda x: str(x), all_audio_files))
    return all_audio_files


def tempo_extractor(file):
    key = os.path.basename(file).replace('.LOFI.mp3', '').replace('.mp3', '').replace('.wav', '')
    return (key, feature_extraction.extract_tempo_features(file, window_length=1024))

def key_extractor(file):
    key = os.path.basename(file).replace('.LOFI.mp3', '').replace('.mp3', '').replace('.wav', '')
    return (key, feature_extraction.extract_key_features(file, window_length=8192))


pp = Pool(10)

def convert_audio_folder_to_joblib(files, extractor):
    result = pp.map(extractor, files)
    result_dict = dict((x, y) for x, y in result)
    return result_dict



def handle(files:list, job_path, extractor):
    calculated = {}
    if os.path.exists(job_path):
        calculated = joblib.load(job_path)
        if calculated is not None:
            calculated_keys = calculated.keys()
            def check(file):
                for key in calculated_keys:
                    if key in file:
                        return False
                return True
            files = list(filter(check, files))
    batch_size = 50
    current = 0
    total_num = len(files)
    while current <= total_num :
        print(f"Processing range of {current}:{current+batch_size} of {total_num}")
        partial = convert_audio_folder_to_joblib(files[current: current + batch_size], extractor)
        if calculated is None:
            calculated = {}
        calculated.update(partial)
        joblib.dump(calculated, job_path)
        print(f"Processed: {len(partial.keys())} {len(calculated.keys())}. Saved.")
        current += batch_size




def main():
    arguments = feature_extraction.parse_arguments()
    audio_folder = arguments.audio_folder
    tempo_features_job_file = join(audio_folder, 'tempo_features.joblib')
    key_features_job_file = join(audio_folder, 'key_features.joblib')
    all_audio_files = lookup_audio_files(audio_folder)


    handle(all_audio_files, tempo_features_job_file, tempo_extractor)
    handle(all_audio_files, key_features_job_file, key_extractor)
    print("all need is completed!")
    pp.close()

main()