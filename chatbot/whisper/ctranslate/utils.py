from ctranslate2.converters.transformers import TransformersConverter

## MODEL RELATING
def model_converter(model, model_output):
    converter = TransformersConverter("openai/whisper-" + model)
    try:
        converter.convert(model_output, None, "float16", False)
    except Exception as e:
        print(e)
