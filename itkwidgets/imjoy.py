from dataclasses import dataclass, asdict

from typing import Dict

import itkwasm
import numcodecs
from imjoy import api

_numcodec_encoder = numcodecs.Blosc(cname='lz4', clevel=3)
_numcodec_config = _numcodec_encoder.get_config()

def encode_itkwasm_image(image):
    global _numcodec_encoder

    image_dict = asdict(image)

    image_data = image_dict['data']
    encoded_data = _numcodec_encoder.encode(image_data)
    image_dict['data'] = { 'buffer': encoded_data, 'config': _numcodec_config, 'nbytes': image_data.nbytes }

    image_direction = image_dict['direction']
    encoded_direction = _numcodec_encoder.encode(image_direction)
    image_dict['direction'] = { 'buffer': encoded_direction, 'config': _numcodec_config, 'nbytes': image_direction.nbytes }

    return image_dict

def register_itkwasm_imjoy_codecs():

    api.registerCodec({'name': 'itkwasm-image', 'type': itkwasm.Image, 'encoder': encode_itkwasm_image})
