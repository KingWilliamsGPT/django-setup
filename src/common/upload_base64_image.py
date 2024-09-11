import base64
import os
import os.path


from django.core.files.base import ContentFile
from django.conf import settings
from easy_thumbnails.files import get_thumbnailer
from PIL import Image



def _decode_b64(data):
    try:
        decoded_bytes = base64.b64decode(data)
        return decoded_bytes
    except Exception as e:
        raise



def save_base64_image(model_instance, model_field, base64_content, dest_file_name):
    decoded_bytes = _decode_b64(base64_content)

    # ensure the directory to put the file exists
    dirname = os.path.dirname(dest_file_name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    file_name = dest_file_name
    with open(file_name, 'wb') as file:
        file.write(decoded_bytes)

    image = Image.open(file.name)
    ext = image.format

    with open(file_name, 'rb') as file:
        thumbnail = get_thumbnailer(file, relative_name=f'{os.path.basename(file.name)}.{ext}')
        setattr(model_instance, model_field, thumbnail) # product.thumbnail = thumbnail
        model_instance.save()