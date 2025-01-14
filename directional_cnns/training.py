"""
Main entry point to train multiple models and predict on test sets.
"""

import argparse
import datetime
import time
from os.path import join

import tensorflow as tf
import joblib
from sklearn.preprocessing import OneHotEncoder
from keras import backend as K
from keras.callbacks import ModelCheckpoint, EarlyStopping, TensorBoard
from keras.models import load_model, Model
from keras.optimizers import Adam
from tensorflow.python.lib.io.file_io import FileIO, file_exists

from directional_cnns.cloudml_utils import create_local_copy, save_model, make_missing_dirs
from directional_cnns.loader import create_mel_sample_loader, create_cq_sample_loader
from directional_cnns.prediction import predict
from directional_cnns.generator import DataGenerator, tempo_augmenter, key_augmenter
from directional_cnns.groundtruth import TempoGroundTruth, KeyGroundTruth
from directional_cnns.models import ModelLoader
from directional_cnns.network.shallow import create_shallow_key_model, create_shallow_tempo_model
from directional_cnns.network.vgg import create_vgg_like_model
from directional_cnns.normalizer import std_normalizer


def train_and_predict(train_file, valid_file, test_files, feature_files, job_dir, model_dir):
    """
    Main function to execute training and prediction of all architecture variations.

    :param train_file: training ground truth in .tsv format
    :param valid_file: validation ground truth in .tsv format
    :param test_files: comma-separated validation ground truths in .tsv format
    :param feature_files: comma-separated feature dictionaries in .joblib format
    :param job_dir: working directory
    :param model_dir: directory to store models and predictions in
    """
    log_file_name = join(job_dir, 'log-{}.txt'.format(time.strftime("%Y%m%d-%H%M%S")))
    make_missing_dirs(log_file_name)
    print('Logging to {}'.format(log_file_name))
    with FileIO(log_file_name, mode='w') as log_file:

        def log(message):
            message_bytes = '{}\n'.format(message).encode(encoding='utf-8')
            log_file.write(message_bytes)
            print(message)

        log('Starting train and predict. {}\n'.format(datetime.datetime.now()))

        if tf.test.gpu_device_name():
            log('Default GPU: {}'.format(tf.test.gpu_device_name()))
        else:
            log("Failed to find default GPU.")

        log('Creating local copies, if necessary...')

        train_file = create_local_copy(train_file)
        valid_file = create_local_copy(valid_file)
        test_files = [create_local_copy(test_file) for test_file in test_files.split(',')]
        feature_files = [create_local_copy(feature_file) for feature_file in feature_files.split(',')]

        # add validation set to test sets, so that it always gets evaluated
        test_files.insert(0, valid_file)

        features = {}
        for feature_file in feature_files:
            features.update(joblib.load(feature_file))
        log('Loaded features for {} files from {}.'.format(len(features), feature_files))

        normalizer = std_normalizer

        # tempo or key?
        first_feature = features[list(features.keys())[0]]
        if is_tempo_feature(first_feature):
            log('We assume that we are estimating TEMPO. First feature shape: {}'.format(first_feature.shape))
            augmenter = tempo_augmenter
            input_shape = (40, 256, 1)
            train_loader = create_mel_sample_loader(features, shape=input_shape, random_offset=True,
                                                    normalizer=normalizer)
            valid_loader = create_mel_sample_loader(features, shape=input_shape, random_offset=False,
                                                    normalizer=normalizer)
            log('Loading ground truth...')

            train_ground_truth = TempoGroundTruth(train_file)
            log('Loaded {} training annotations from {}.'.format(len(train_ground_truth.labels), train_file))

            valid_ground_truth = TempoGroundTruth(valid_file)
            log('Loaded {} validation annotations from {}.'.format(len(valid_ground_truth.labels), valid_file))


        else:
            log('We assume that we are estimating KEY. First feature shape: {}'.format(first_feature.shape))
            augmenter = key_augmenter
            input_shape = (168, 60, 1)
            train_loader = create_cq_sample_loader(features, shape=input_shape, random_offset=True,
                                                   normalizer=normalizer)
            valid_loader = create_cq_sample_loader(features, shape=input_shape, random_offset=False,
                                                   normalizer=normalizer)

            log('Loading ground truth...')

            train_ground_truth = KeyGroundTruth(train_file)
            log('Loaded {} training annotations from {}.'.format(len(train_ground_truth.labels), train_file))

            valid_ground_truth = KeyGroundTruth(valid_file)
            log('Loaded {} validation annotations from {}.'.format(len(valid_ground_truth.labels), valid_file))

        batch_size = 64
        lr = 0.001
        epochs = 5000 # 5000 ?
        patience = 100 # 150 ?
        filters = 4
        dropout = 0.3
        runs = 3 # 3

        nb_classes = len(train_ground_truth.classes())
        log('Number of classes: {}'.format(nb_classes))
        log('Creating generators...')
        log('Creating model...')

        def create_shallow_key(filters=filters, dropout=dropout):
            return create_shallow_key_model(input_shape=input_shape, output_dim=nb_classes, filters=filters,
                                            short_filter_length=3,
                                            long_filter_length=input_shape[0],
                                            dropout=dropout)

        def create_shallow_tempo(filters=filters, dropout=dropout):
            return create_shallow_tempo_model(input_shape=input_shape, output_dim=nb_classes, filters=filters,
                                              short_filter_length=3,
                                              long_filter_length=input_shape[1],
                                              dropout=dropout)

        def create_rectangular_tempo_vgg_max(filters=filters, dropout=dropout):
            max_pool_shape = (2, 2)
            filter_shapes = [(1, 5), (1, 3)]

            return create_vgg_like_model(input_shape=input_shape, output_dim=nb_classes, filters=filters,
                                         pool_shape=max_pool_shape, filter_shapes=filter_shapes, dropout=dropout)

        def create_rectangular_key_vgg_max(filters=filters, dropout=dropout):
            max_pool_shape = (2, 2)
            filter_shapes = [(5, 1), (3, 1)]

            return create_vgg_like_model(input_shape=input_shape, output_dim=nb_classes, filters=filters,
                                         pool_shape=max_pool_shape, filter_shapes=filter_shapes, dropout=dropout)

        def create_square_vgg_max(filters=filters, dropout=dropout):
            max_pool_shape = (2, 2)
            filter_shapes = [(5, 5), (3, 3)]

            return create_vgg_like_model(input_shape=input_shape, output_dim=nb_classes, filters=filters,
                                         pool_shape=max_pool_shape, filter_shapes=filter_shapes, dropout=dropout)

        create_model_functions = [create_shallow_key,
                                  create_shallow_tempo,
                                  create_rectangular_tempo_vgg_max,
                                  create_rectangular_key_vgg_max,
                                  create_square_vgg_max]

        creation_filter = {'square_vgg': [1, 2, 4, 8, 16, 24], 'vgg': [2, 4, 8, 16, 24], 'shallow': [1, 2, 4, 6, 8, 12]}
        creation_dropout = [0.1, 0.3, 0.5]

        models = {}

        for create_model in create_model_functions:
            if 'vgg' in create_model.__name__:
                if 'square' in create_model.__name__:
                    filters = creation_filter['square_vgg']
                else:
                    filters = creation_filter['vgg']
            if 'shallow' in create_model.__name__:
                filters = creation_filter['shallow']

            for f in filters:
                for d in creation_dropout:
                    same_kind_models = []
                    for run in range(runs):
                        model = create_model(**{'filters': f, 'dropout': d})
                        model_loader = train(run=run, epochs=epochs, patience=patience, batch_size=batch_size, lr=lr,
                                      input_shape=input_shape, model=model, augmenter=augmenter,
                                      train_ground_truth=train_ground_truth, valid_ground_truth=valid_ground_truth,
                                      train_loader=train_loader, valid_loader=valid_loader, model_dir=model_dir, log=log)
                        same_kind_models.append(model_loader)
                        K.clear_session()
                    model_name = same_kind_models[0].name
                    models[model_name] = same_kind_models

        log('Trained on {}'.format(train_file))
        log('runs={}, lr={}, batch_size={}, epochs={}, patience={}, augmenter={}, normalizer={}'
              .format(runs, lr, batch_size, epochs, patience, augmenter, normalizer))

        latex_report_whole, plain_report_whole = train_ground_truth.create_accuracy_reports(features,
                                    input_shape, False, log, models, normalizer, test_files, predict)
        log('')
        log(latex_report_whole)
        log('')
        log(plain_report_whole)
        log('')


def is_tempo_feature(feature):
    tempo_features = feature.shape[0] == 40
    return tempo_features

def file_safe_name(name):
    return name.replace('/','=')

def train(run=0, epochs=5000, patience=50, batch_size=32, lr=0.001, model:Model=None, input_shape=(40, 256, 1),
          augmenter=None, train_ground_truth=None, valid_ground_truth=None, train_loader=None, valid_loader=None,
          model_dir='./', log=None):
    # and save to model_dir
    model_file = join(model_dir, 'model_{}_run={}.h5'.format(file_safe_name(model.name), run))
    if file_exists(model_file):
        log('Model file {} already exists. Skipping training.'.format(model_file))
        return ModelLoader(model_file, model.name)
    else:
        checkpoint_model_file = 'checkpoint_model.h5'
        binarizer = OneHotEncoder(sparse=False)
        binarizer.fit([[c] for c in range(train_ground_truth.nb_classes)])
        model.compile(loss='categorical_crossentropy', optimizer=Adam(learning_rate=lr), metrics=['accuracy'])
        log('Run {}, {}, params={}'.format(run, model.name, model.count_params()))
        log(model.summary())
        train_generator = DataGenerator(train_ground_truth,
                                        train_loader,
                                        binarizer, batch_size=batch_size,
                                        sample_shape=input_shape, shuffle=True, augmenter=augmenter)
        valid_generator = DataGenerator(valid_ground_truth,
                                        valid_loader,
                                        binarizer, batch_size=batch_size,
                                        sample_shape=input_shape, shuffle=False, augmenter=None)
        logdir = "tf_logs/scalars/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        tensorboard_callback = TensorBoard(log_dir=logdir)

        callbacks = [EarlyStopping(monitor='val_loss', patience=patience, verbose=1),
                     ModelCheckpoint(checkpoint_model_file, monitor='val_loss'),
                     tensorboard_callback]
        model.fit(train_generator, epochs=epochs, callbacks=callbacks,
                                      validation_data=valid_generator)
        log(model.summary())
        log('lr={}, batch_size={}, epochs={}, augmenter={}, model_name={}'
              .format(lr, batch_size, epochs, augmenter, model.name))
        log('Run {}, {}, params={}'.format(run, model.name, model.count_params()))
        model = load_model(checkpoint_model_file)
        save_model(model, model_file)
        return ModelLoader(model_file, model.name)


def parse_arguments():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''Main entry point for training and evaluating different models.   
Both feature .joblib files and TSV ground truth files have to be provided.

License: CC BY 3.0''')

    # Input Arguments
    parser.add_argument(
        '--train-file',
        help='Training ground truth.',
        required=True
    )
    parser.add_argument(
        '--valid-file',
        help='Validation ground truth.',
        required=True
    )
    parser.add_argument(
        '--test-files',
        help='Test ground truth.',
        required=True
    )
    parser.add_argument(
        '--feature-files',
        help='One or more comma-separated mel feature files that provide features'
             ' for all data sets.',
        required=True
    )
    parser.add_argument(
        '--job-dir',
        help='output directory',
        required=True
    )
    parser.add_argument(
        '--model-dir',
        help='model directory',
        required=True
    )

    args = parser.parse_args()
    arguments = args.__dict__
    return arguments


def main():
    arguments = parse_arguments()
    train_and_predict(**arguments)


if __name__ == '__main__':
    main()
