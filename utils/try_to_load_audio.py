

import joblib
from sklearn.preprocessing import OneHotEncoder
from directional_cnns.generator import DataGenerator
from directional_cnns.groundtruth import TempoGroundTruth
from directional_cnns.loader import create_cq_sample_loader
from directional_cnns.normalizer import std_normalizer

feature_files=["/home/xvan/dataset/sound/GTZAN/Data/key_features.joblib",
               "/home/xvan/dataset/sound/giantsteps-mtg-key-dataset/key_features.joblib",
               "/home/xvan/dataset/sound/giantsteps-key-dataset/key_features.joblib",
               "/home/xvan/dataset/sound/lmd_matched_mp3/key_features.joblib",
               ]
features = {}
for feature_file in feature_files:
    features.update(joblib.load(feature_file))

input_shape = (168, 60, 1)
normalizer = std_normalizer
train_loader = create_cq_sample_loader(features, shape=input_shape, random_offset=True,
                                        normalizer=normalizer)
valid_loader = create_cq_sample_loader(features, shape=input_shape, random_offset=False,
                                        normalizer=normalizer)
train_ground_truth=TempoGroundTruth("annotations/key_train.tsv")
valid_ground_truth=TempoGroundTruth("annotations/key_valid.tsv")
create_cq_sample_loader(features, shape=input_shape, random_offset=True,
                                                   normalizer=normalizer)

binarizer = OneHotEncoder(sparse_output=False)
binarizer.fit([[c] for c in range(train_ground_truth.nb_classes)])

batch_size=32

train_generator = DataGenerator(train_ground_truth,
                                train_loader,
                                binarizer, batch_size=batch_size,
                                sample_shape=input_shape, shuffle=True, augmenter=None)
valid_generator = DataGenerator(valid_ground_truth,
                                valid_loader,
                                binarizer, batch_size=batch_size,
                                sample_shape=input_shape, shuffle=False, augmenter=None)

try:
    for x in enumerate(train_generator):
        pass
except:
    print("Error")