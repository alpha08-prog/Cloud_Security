"""Documented 2024 architectures; lazy TensorFlow dependency, not a trained model.

Input collection, scaling and run-level splits must be validated separately.
"""


def service_models(feature_count=411, window=6):
    import tensorflow as tf
    from tensorflow import keras

    source = keras.Input((feature_count,))
    x = source
    for width in (512, 256, 128):
        x = keras.layers.Dense(width, activation="relu")(x)
    encoded = keras.layers.Dense(20, activation="sigmoid")(x)
    x = encoded
    for width in (128, 256, 512):
        x = keras.layers.Dense(width, activation="relu")(x)
    decoded = keras.layers.Dense(feature_count, activation="sigmoid")(x)
    autoencoder = keras.Model(source, decoded)
    def rmse(actual, predicted):
        return tf.sqrt(tf.reduce_mean(tf.square(actual - predicted)) + 1e-12)
    autoencoder.compile(optimizer=keras.optimizers.Adam(1e-4), loss=rmse)
    encoder = keras.Model(source, encoded)
    classifier = keras.Sequential([
        keras.Input((window, 20)),
        keras.layers.LSTM(1024, return_sequences=True),
        keras.layers.LSTM(512),
        keras.layers.Dense(512, activation="relu"),
        keras.layers.Dense(256, activation="relu"),
        keras.layers.Dense(2, activation="softmax"),
    ])
    classifier.compile(optimizer=keras.optimizers.Adam(1e-4), loss="sparse_categorical_crossentropy")
    return autoencoder, encoder, classifier
