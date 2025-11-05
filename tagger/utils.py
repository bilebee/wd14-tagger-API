"""Utility functions for the tagger module"""
import os

from typing import List, Dict
from pathlib import Path

# Standalone mode settings
shared = type('Shared', (), {})()
models_path = os.path.join(os.getcwd(), "models")
shared.models_path = models_path
shared.cmd_opts = type('CmdOpts', (), {})()
HAS_SD = False

default_ddp_path = Path(shared.models_path, 'deepdanbooru')
default_onnx_path = Path(shared.models_path, 'TaggerOnnx')

from tagger.preset import Preset  # pylint: disable=import-error
from tagger.interrogator import Interrogator, DeepDanbooruInterrogator, \
                                WaifuDiffusionInterrogator  # pylint: disable=E0401 # noqa: E501

# Simplified preset handling for standalone mode
preset = Preset(Path('presets'))

interrogators: Dict[str, Interrogator] = {
    'wd14-vit.v1': WaifuDiffusionInterrogator(
        'WD14 ViT v1',
        repo_id='SmilingWolf/wd-v1-4-vit-tagger'
    ),
    'wd14-vit.v2': WaifuDiffusionInterrogator(
        'WD14 ViT v2',
        repo_id='SmilingWolf/wd-v1-4-vit-tagger-v2',
    ),
    'wd14-convnext.v1': WaifuDiffusionInterrogator(
        'WD14 ConvNeXT v1',
        repo_id='SmilingWolf/wd-v1-4-convnext-tagger'
    ),
    'wd14-convnext.v2': WaifuDiffusionInterrogator(
        'WD14 ConvNeXT v2',
        repo_id='SmilingWolf/wd-v1-4-convnext-tagger-v2',
    ),
    'wd14-convnextv2.v1': WaifuDiffusionInterrogator(
        'WD14 ConvNeXTV2 v1',
        # the name is misleading, but it's v1
        repo_id='SmilingWolf/wd-v1-4-convnextv2-tagger-v2',
    ),
    'wd14-swinv2-v1': WaifuDiffusionInterrogator(
        'WD14 SwinV2 v1',
        # again misleading name
        repo_id='SmilingWolf/wd-v1-4-swinv2-tagger-v2',
    ),
    'wd-v1-4-moat-tagger.v2': WaifuDiffusionInterrogator(
        'WD14 moat tagger v2',
        repo_id='SmilingWolf/wd-v1-4-moat-tagger-v2'
    ),
}


def refresh_interrogators() -> List[str]:
    """Refreshes the interrogators list"""
    # load deepdanbooru project
    ddp_path = os.environ.get('DEEPDANBOORU_PROJECTS_PATH', default_ddp_path)
    onnx_path = os.environ.get('ONNXTAGGER_PATH', default_onnx_path)
    os.makedirs(ddp_path, exist_ok=True)
    os.makedirs(onnx_path, exist_ok=True)

    for path in os.scandir(ddp_path):
        print(f"Scanning {path} as deepdanbooru project")
        if not path.is_dir():
            print(f"Warning: {path} is not a directory, skipped")
            continue

        if not Path(path, 'project.json').is_file():
            print(f"Warning: {path} has no project.json, skipped")
            continue

        interrogators[path.name] = DeepDanbooruInterrogator(path.name, path)
    # scan for onnx models as well
    for path in os.scandir(onnx_path):
        print(f"Scanning {path} as onnx model")
        if not path.is_dir():
            print(f"Warning: {path} is not a directory, skipped")
            continue

        # Check for ONNX model files
        onnx_files = [x for x in os.scandir(path) if x.name.endswith('.onnx')]
        
        if len(onnx_files) != 1:
            print(f"Warning: {path} requires exactly one .onnx model, skipped")
            continue
            
        local_model_path = Path(path, onnx_files[0].name)

        csv = [x for x in os.scandir(path) if x.name.endswith('.csv')]
        if len(csv) == 0:
            print(f"Warning: {path} has no selected tags .csv file, skipped")
            continue

        def tag_select_csvs_up_front(k):
            return sum(-1 if t in k.name.lower() else 1 for t in ["tag", "select"])

        csv.sort(key=tag_select_csvs_up_front)
        tags_path = Path(path, csv[0])

        if path.name not in interrogators:
            # Create new interrogator for local ONNX model
            interrogators[path.name] = WaifuDiffusionInterrogator(
                path.name,
                model_path=onnx_files[0].name,
                is_hf=False
            )

        interrogators[path.name].local_model = str(local_model_path)
        interrogators[path.name].local_tags = str(tags_path)
        interrogators[path.name].model_type = "onnx"  # Store model type

    return sorted(interrogators.keys())


def split_str(string: str, separator=',') -> List[str]:
    return [x.strip() for x in string.split(separator) if x]