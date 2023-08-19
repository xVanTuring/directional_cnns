feature_dir=~/dataset/tempo-key-features
directional_cnn_training --job-dir=./ --model-dir=./ --train-file=annotations/key_train.tsv --valid-file=annotations/key_valid.tsv \
	--test-files=annotations/giantsteps-key.tsv,annotations/gtzan_key.tsv,annotations/lmd_key_test.tsv \
	--feature-files=$feature_dir/giant_key_key_features.joblib,$feature_dir/mtg_key_features.joblib,$feature_dir/giant_key_key_features.joblib,$feature_dir/lmd_key_features.joblib
