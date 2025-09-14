from keras.models import load_model as keras_load_model


def load_saved_model():
    return keras_load_model('models/solar_panel_model.h5')

def print_model_summary():
    model = load_saved_model()
    model.summary()

print_model_summary()
