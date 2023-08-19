directional_cnn_training --job-dir=./ --model-dir=./ --train-file=annotations/key_train.tsv --valid-file=annotations/key_valid.tsv \
	--test-files=annotations/giantsteps-key.tsv,annotations/gtzan_key.tsv,annotations/lmd_key_test.tsv \
	--feature-files=/home/xvan/dataset/sound/GTZAN/Data/key_features.joblib,/home/xvan/dataset/sound/giantsteps-mtg-key-dataset/key_features.joblib,/home/xvan/dataset/sound/giantsteps-key-dataset/key_features.joblib,/home/xvan/dataset/sound/lmd_matched_mp3/key_features.joblib

# python training.py --job-dir=./ --model-dir=./ --train-file=annotations/key_train.tsv --valid-file=annotations/key_valid.tsv \
# 	--test-files=annotations/giantsteps-key.tsv,annotations/gtzan_key.tsv,annotations/lmd_key_test.tsv \
# 	--feature-files=/home/xvan/dataset/sound/GTZAN/Data/key_features.joblib,/home/xvan/dataset/sound/giantsteps-mtg-key-dataset/key_features.joblib,/home/xvan/dataset/sound/giantsteps-key-dataset/key_features.joblib,/home/xvan/dataset/sound/lmd_matched_mp3/key_features.joblib
