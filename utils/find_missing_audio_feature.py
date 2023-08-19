from pathlib import Path
from directional_cnns.groundtruth import TempoGroundTruth


# "annotations/key_train.tsv","annotations/key_valid.tsv",
only_in_ground_truth=['annotations/giantsteps-key.tsv',"annotations/gtzan_key.tsv","annotations/lmd_key_test.tsv"]

def get_files(root_dir,extensions):
    all_files = []
    for ext in extensions:
        all_files.extend(Path(root_dir).rglob(ext))
    return all_files


audio_folder = "/home/xvan/dataset/sound"

def to_key(path):
    return path.name.replace('.LOFI.mp3', '').replace('.mp3', '').replace('.wav', '')
all_audio_files = set(list(map(to_key, get_files(audio_folder,["*.mp3","*.LOFI.mp3", "*.wav", "*.flac"]))))


ground_truths = list(map(lambda x:TempoGroundTruth(x), only_in_ground_truth))

keys = list(map(lambda x:list(x.labels.keys()),ground_truths))
def flatten(l):
    return [item for sublist in l for item in sublist]

keys = flatten(keys)
print(f"total of {len(keys)} from {len(all_audio_files)}")
for k in keys:
    if k not in all_audio_files:
        print(f"Missing audio with key {k}")

