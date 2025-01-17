import os

from datasets import load_dataset
import pandas as pd
import pytest
import requests

import tune_the_model as ttm


@pytest.fixture(scope='session')
def configured_model_one():
    ttm.set_api_key(os.environ.get("TTM_API_KEY"))


@pytest.fixture(scope="session")
def dataset():
    yield load_dataset("tweet_eval", "irony")


@pytest.fixture(scope="module")
def classifier(configured_model_one, tmpdir_factory, dataset):
    train = pd.DataFrame(dataset['train'])
    validation = pd.DataFrame(dataset['validation'])

    model = ttm.tune_classifier(
        tmpdir_factory.mktemp("models").join("classifier.json"),
        train['text'], 
        train['label'], 
        validation['text'], 
        validation['label'],
        train_iters=10
    )

    yield model

    model.delete()


def test_train_classifier(classifier):
    assert classifier.status in {
        ttm.TuneTheModelStatus.READY,
        ttm.TuneTheModelStatus.TRAINING,
        ttm.TuneTheModelStatus.TRAIN_REQUESTED,
        ttm.TuneTheModelStatus.INQUEUE
    }


def test_train_classifier_with_large_dataset(configured_model_one, tmpdir_factory, dataset):
    data = pd.DataFrame(dataset["train"])

    data = pd.concat([data] * 10)

    model = ttm.TuneTheModel.create_classifier(
        tmpdir_factory.mktemp("models").join("classifier-with-large-dataset.json"),
        train_iters=10,
    )

    with pytest.raises(ttm.TuneTheModelException) as exc:
        model.fit(
            X=data["text"],
            y=data["label"],
        )
    assert "Payload exceeds the limit" in str(exc.value)

    model.delete()


@pytest.fixture(scope="module")
def trained_classifier(classifier):
    classifier.wait_for_training_finish()

    yield classifier


def test_trained_classifier(trained_classifier, dataset):
    assert trained_classifier.status == ttm.TuneTheModelStatus.READY

    validation = pd.DataFrame(dataset['validation'])

    res_validation = []
    for text in dataset['validation']['text']:
        res_validation += trained_classifier.classify(input=text)

    assert len(res_validation) > 0


@pytest.fixture(scope="module")
def generator(configured_model_one, tmpdir_factory, dataset):
    train_inputs = ["алый", "альбом"] * 32
    train_outputs = ["escarlata", "el álbum"] * 32
    validation_inputs = ["бассейн", "бахрома"] * 32
    validation_outputs = ["libre", "flecos"] * 32

    model = ttm.tune_generator(
        tmpdir_factory.mktemp("models").join("generator.json"),
        train_inputs,
        train_outputs,
        validation_inputs,
        validation_outputs,
        train_iters=10
    )

    yield model

    model.delete()


def test_generator(generator):
    assert generator.status in {
        ttm.TuneTheModelStatus.READY,
        ttm.TuneTheModelStatus.TRAINING,
        ttm.TuneTheModelStatus.TRAIN_REQUESTED,
        ttm.TuneTheModelStatus.INQUEUE
    }


@pytest.fixture(scope="module")
def trained_generator(generator):
    generator.wait_for_training_finish()

    yield generator


def test_trained_generator(trained_generator):
    assert trained_generator.status == ttm.TuneTheModelStatus.READY

    assert len(trained_generator.generate("бассейн")) > 0