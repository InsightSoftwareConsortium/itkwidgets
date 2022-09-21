from dataclasses import asdict

from typing import Dict 

import itkwasm
import numcodecs
from imjoy_rpc import api
import zarr

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

def encode_zarr_store(store):
    def getItem(key):
        return store[key]

    def setItem(key, value):
        store[key] = value

    def containsItem(key):
        return key in store

    return {
        "_rintf": True,
        "_rtype": 'zarr-store',
        "getItem": getItem,
        "setItem": setItem,
        "containsItem": containsItem,
    }

def register_itkwasm_imjoy_codecs():

    api.registerCodec({'name': 'itkwasm-image', 'type': itkwasm.Image, 'encoder': encode_itkwasm_image})
    api.registerCodec({'name': 'zarr-store', 'type': zarr.storage.BaseStore, 'encoder': encode_zarr_store})
 
