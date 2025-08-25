""" Interrogator class and subclasses for tagger """
import os
from pathlib import Path
import io
import json
import inspect
from re import match as re_match
from platform import system, uname
from typing import Tuple, List, Dict, Callable
from pandas import read_csv
from PIL import Image, UnidentifiedImageError
from numpy import asarray, float32, expand_dims, exp
from tqdm import tqdm

try:
    from huggingface_hub import hf_hub_download
    HAS_HUGGINGFACE = True
except ImportError:
    HAS_HUGGINGFACE = False
    hf_hub_download = None

try:
    from modules.paths import extensions_dir
    from modules import shared
    HAS_SD = True
except ImportError:
    # Standalone mode settings
    extensions_dir = os.path.dirname(os.path.abspath(__file__))
    shared = type('Shared', (), {})()
    shared.models_path = os.path.join(os.getcwd(), "models")
    shared.cmd_opts = type('CmdOpts', (), {})()
    # Set default values for cmd_opts attributes
    shared.cmd_opts.use_cpu = []
    shared.cmd_opts.additional_device_ids = None
    # Create opts for standalone mode
    shared.opts = type('Opts', (), {})()
    shared.opts.tagger_hf_cache_dir = os.path.join(os.getcwd(), "cache")
    HAS_SD = False

from tagger import settings  # pylint: disable=import-error
from tagger.uiset import QData, IOData  # pylint: disable=import-error
from . import dbimutils  # pylint: disable=import-error # noqa

Its = settings.InterrogatorSettings

# select a device to process
try:
    use_cpu = ('all' in shared.cmd_opts.use_cpu) or (
        'interrogate' in shared.cmd_opts.use_cpu) if HAS_SD and shared and shared.cmd_opts else False
except AttributeError:
    use_cpu = False

# https://onnxruntime.ai/docs/execution-providers/
# https://github.com/toriato/stable-diffusion-webui-wd14-tagger/commit/e4ec460122cf674bbf984df30cdb10b4370c1224#r92654958
onnxrt_providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

if HAS_SD and shared and shared.cmd_opts and shared.cmd_opts.additional_device_ids is not None:
    m = re_match(r'([cg])pu:\d+$', shared.cmd_opts.additional_device_ids)
    if m is None:
        raise ValueError('--device-id is not cpu:<nr> or gpu:<nr>')
    if m.group(1) == 'c':
        onnxrt_providers.pop(0)
    TF_DEVICE_NAME = f'/{shared.cmd_opts.additional_device_ids}'
elif use_cpu:
    TF_DEVICE_NAME = '/cpu:0'
    onnxrt_providers.pop(0)
else:
    TF_DEVICE_NAME = '/gpu:0'

print(f'== WD14 tagger {TF_DEVICE_NAME}, {uname()} ==')


def get_onnxrt():
    """Get ONNX runtime module with error handling for standalone mode"""
    try:
        import onnxruntime as ort
        return ort
    except ImportError:
        raise ImportError(
            "Please install onnxruntime to use ONNX models: "
            "pip install onnxruntime"
        )


class Interrogator:
    """ Interrogator class for tagger """
    # the raw input and output.
    input = {
        "cumulative": False,
        "large_query": False,
        "unload_after": False,
        "add": '',
        "keep": '',
        "exclude": '',
        "search": '',
        "replace": '',
        "output_dir": '',
    }
    output = None
    odd_increment = 0

    @classmethod
    def flip(cls, key):
        def toggle():
            cls.input[key] = not cls.input[key]
        return toggle

    @staticmethod
    def get_errors() -> str:
        errors = ''
        if len(IOData.err) > 0:
            # write errors in html pointer list, every error in a <li> tag
            errors = IOData.error_msg()
        if len(QData.err) > 0:
            errors += 'Fix to write correct output:<br><ul><li>' + \
                      '</li><li>'.join(QData.err) + '</li></ul>'
        return errors

    @classmethod
    def set(cls, key: str) -> Callable[[str], Tuple[str, str]]:
        def setter(val) -> Tuple[str, str]:
            if key == 'input_glob':
                IOData.update_input_glob(val)
                return (val, cls.get_errors())
            if val != cls.input[key]:
                tgt_cls = IOData if key == 'output_dir' else QData
                getattr(tgt_cls, "update_" + key)(val)
                cls.input[key] = val
            return (cls.input[key], cls.get_errors())

        return setter

    @staticmethod
    def load_image(path: str) -> Image:
        try:
            return Image.open(path)
        except FileNotFoundError:
            print(f'${path} not found')
            return None
        except UnidentifiedImageError as e:
            print(f'${path} is not an image: ${e}')
            return None

    def __init__(self, name: str) -> None:
        self.name = name
        self.model = None

    def load(self) -> None:
        raise NotImplementedError()

    def unload(self) -> bool:
        unloaded = False
        if self.model is not None:
            del self.model
            self.model = None
            unloaded = True
            print(f'Unloaded {self.name} model')
        return unloaded

    def interrogate(
        self,
        image: Image
    ) -> Tuple[
        Dict[str, float],  # rating confidents
        Dict[str, float]  # tag confidents
    ]:
        raise NotImplementedError()


# brought from https://github.com/KichangKim/DeepDanbooru/blob/master/deepdanbooru/data/__init__.py
def replace_fc_to_blank(text: str) -> str:
    """
    Replace forbidden characters to blank character.
    """
    if text is None:
        return ''

    return text.translate(str.maketrans({
        c: ' ' for c in
        ['"', '*', '/', ':', '<', '>', '?', '\\', '|', '+', '[', ']']
    }))


class DeepDanbooruInterrogator(Interrogator):
    """ DeepDanbooru Interrogator class """
    def __init__(self, name: str, project_path: os.PathLike) -> None:
        super().__init__(name)
        self.project_path = project_path
        self.model = None
        self.tags = None

    def load(self) -> None:
        print(f'Loading {self.name} from {str(self.project_path)}')

        # deepdanbooru package is not include in web-sd anymore
        # https://github.com/AUTOMATIC1111/stable-diffusion-webui/commit/c81d440d876dfd2ab3560410f37442ef56fc663
        try:
            import deepdanbooru
        except ImportError:
            raise ImportError(
                "Please install deepdanbooru to use DeepDanbooru models: "
                "pip install git+https://github.com/KichangKim/DeepDanbooru.git"
            )

        import tensorflow as tf

        # tensorflow maps nearly all vram by default, so we limit this
        # https://www.tensorflow.org/guide/gpu#limiting_gpu_memory_growth
        # TODO: only run on the first run
        for device in tf.config.experimental.list_physical_devices('GPU'):
            try:
                tf.config.experimental.set_memory_growth(device, True)
            except RuntimeError as err:
                print(err)

        with tf.device(TF_DEVICE_NAME):
            import deepdanbooru.project as ddp

            self.model = ddp.load_model_from_project(
                project_path=self.project_path,
                compile_model=False
            )

            print(f'Loaded {self.name} model from {str(self.project_path)}')

            self.tags = ddp.load_tags_from_project(
                project_path=self.project_path
            )

    def unload(self) -> bool:
        # For TensorFlow models, unloading is non-trivial
        # Return False to indicate model wasn't actually unloaded
        return False

    def interrogate(
        self,
        image: Image
    ) -> Tuple[
        Dict[str, float],  # rating confidences
        Dict[str, float]  # tag confidences
    ]:
        # init model
        if self.model is None:
            self.load()

        import deepdanbooru.data as ddd

        # convert an image to fit the model
        image_bufs = io.BytesIO()
        image.save(image_bufs, format='PNG')
        image = ddd.load_image_for_evaluate(
            image_bufs,
            self.model.input_shape[2],
            self.model.input_shape[1]
        )

        image = image.reshape((1, *image.shape[0:3]))

        # evaluate model
        result = self.model.predict(image)

        confidences = result[0].tolist()
        ratings = {}
        tags = {}

        for i, tag in enumerate(self.tags):
            if tag[:7] != "rating:":
                tags[tag] = confidences[i]
            else:
                ratings[tag[7:]] = confidences[i]

        return ratings, tags


class WaifuDiffusionInterrogator(Interrogator):
    """ WaifuDiffusion Interrogator class """
    def __init__(
        self,
        name: str,
        model_path='model.onnx',
        tags_path='selected_tags.csv',
        repo_id=None,
        is_hf=True,
    ) -> None:
        super().__init__(name)
        self.repo_id = repo_id
        self.model_path = model_path
        self.tags_path = tags_path
        self.tags = None
        self.model = None
        self.tags = None
        self.local_model = None
        self.local_tags = None
        self.is_hf = is_hf
        self.model_type = "onnx"  # Default to ONNX

    def download(self) -> Tuple[str, str]:
        """Download model and tags from HuggingFace or use local files"""
        if not self.is_hf:
            # Use local files
            if self.local_model and self.local_tags:
                return self.local_model, self.local_tags
            else:
                raise ValueError("Local model and tags paths must be provided for local models")
        
        # Download from HuggingFace
        if not HAS_HUGGINGFACE:
            raise ImportError(
                "Please install huggingface_hub to download models: "
                "pip install huggingface-hub"
            )
        
        cache = getattr(shared.opts, 'tagger_hf_cache_dir', os.path.join(os.getcwd(), "cache"))
        os.makedirs(cache, exist_ok=True)
        
        print(f"Loading {self.name} model file from {self.repo_id}, "
              f"{self.model_path}")

        model_path = hf_hub_download(
            repo_id=self.repo_id,
            filename=self.model_path,
            cache_dir=cache)
        tags_path = hf_hub_download(
            repo_id=self.repo_id,
            filename=self.tags_path,
            cache_dir=cache)
        
        return model_path, tags_path

    def load(self) -> None:
        # Get model and tags paths
        if self.is_hf:
            model_path, tags_path = self.download()
        else:
            # Use local files
            if not self.local_model or not self.local_tags:
                raise ValueError("Local model and tags paths must be provided for local models")
            model_path = self.local_model
            tags_path = self.local_tags

        # Load based on model type
        if self.model_type == "onnx":
            ort = get_onnxrt()
            self.model = ort.InferenceSession(model_path,
                                              providers=onnxrt_providers)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

        print(f'Loaded {self.name} model from {model_path}')

        self.tags = read_csv(tags_path)

    def interrogate(
        self,
        image: Image
    ) -> Tuple[
        Dict[str, float],  # rating confidences
        Dict[str, float]  # tag confidences
    ]:
        # init model
        if self.model is None:
            self.load()

        # Check model type
        if self.model_type != "onnx":
            raise ValueError(f"Unsupported model type: {self.model_type}")

        # code for converting the image and running the model is taken from the
        # link below. thanks, SmilingWolf!
        # https://huggingface.co/spaces/SmilingWolf/wd-v1-4-tags/blob/main/app.py

        # convert an image to fit the model
        _, height, _, _ = self.model.get_inputs()[0].shape

        # alpha to white
        image = dbimutils.fill_transparent(image)

        image = asarray(image)
        # PIL RGB to OpenCV BGR
        image = image[:, :, ::-1]

        image = dbimutils.make_square(image, height)
        image = dbimutils.smart_resize(image, height)
        image = image.astype(float32)
        image = expand_dims(image, 0)

        # evaluate model
        input_name = self.model.get_inputs()[0].name
        label_name = self.model.get_outputs()[0].name
        confidences = self.model.run([label_name], {input_name: image})[0]

        tags = self.tags[:][['name']]
        tags['confidences'] = confidences[0]

        # first 4 items are for rating (general, sensitive, questionable,
        # explicit)
        ratings = dict(tags[:4].values)

        # rest are regular tags
        tags = dict(tags[4:].values)

        return ratings, tags

    def dry_run(self, images) -> Tuple[str, Callable[[str], None]]:

        def process_images(filepaths, _):
            lines = []
            for image_path in filepaths:
                image_path = image_path.numpy().decode("utf-8")
                lines.append(f"{image_path}\n")
            with io.open("dry_run_read.txt", "a", encoding="utf-8") as filen:
                filen.writelines(lines)

        scheduled = [f"{image_path}\n" for image_path in images]

        # Truncate the file from previous runs
        print("updating dry_run_read.txt")
        io.open("dry_run_read.txt", "w", encoding="utf-8").close()
        with io.open("dry_run_scheduled.txt", "w", encoding="utf-8") as filen:
            filen.writelines(scheduled)
        return process_images