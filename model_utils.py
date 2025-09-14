from keras.models import load_model
import numpy as np
from PIL import Image

# Load the saved model
def load_saved_model():
    return load_model("models/solar_panel_model.h5")

# Preprocess image based on model input shape
def preprocess_image(image_path, input_shape):
    if len(input_shape) == 2:
        # Model expects flat input (e.g., (None, 15876))
        image = Image.open(image_path).convert("L").resize((126, 126))  # grayscale
        arr = np.array(image) / 255.0
        arr = arr.reshape(1, -1)  # flatten
        return arr

    elif len(input_shape) == 4 and input_shape[-1] == 3:
        # Model expects RGB (e.g., (None, 126, 126, 3))
        image = Image.open(image_path).convert("RGB").resize((126, 126))
        arr = np.array(image) / 255.0
        arr = np.expand_dims(arr, axis=0)
        return arr

    elif len(input_shape) == 4 and input_shape[-1] == 1:
        # Model expects grayscale with channel (e.g., (None, 126, 126, 1))
        image = Image.open(image_path).convert("L").resize((126, 126))
        arr = np.array(image) / 255.0
        arr = np.expand_dims(arr, axis=-1)  # add channel dim
        arr = np.expand_dims(arr, axis=0)   # add batch dim
        return arr

    else:
        raise ValueError(f"Unsupported model input shape: {input_shape}")

# Predict function
def predict_image(image_path, threshold=0.65):
    model = load_saved_model()
    input_shape = model.input_shape  # auto-detect model input format
    image_array = preprocess_image(image_path, input_shape)

    prediction = model.predict(image_array)
    print("Raw prediction:", prediction)

    result = "defect" if prediction[0][0] > threshold else "clean"
    print("Final label:", result)
    return result
