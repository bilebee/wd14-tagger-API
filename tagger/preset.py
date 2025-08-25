"""Module for Tagger, to save and load presets."""
import os
import json

from typing import Tuple, List, Dict
from pathlib import Path

try:
    from gradio.context import Context
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False
    Context = type('Context', (), {'block': None})

try:
    from modules.images import sanitize_filename_part  # pylint: disable=E0401
    HAS_SD = True
except ImportError:
    HAS_SD = False
    # Create a simple replacement function
    def sanitize_filename_part(text, replace_spaces=True):
        if text is None:
            return ''
        if replace_spaces:
            text = text.replace(' ', '_')
        # Remove forbidden characters
        forbidden_chars = ['"', '*', '/', ':', '<', '>', '?', '\\', '|', '+', '[', ']']
        for char in forbidden_chars:
            text = text.replace(char, '')
        return text

PresetDict = Dict[str, Dict[str, any]]


class Preset:
    """Preset class for Tagger, to save and load presets."""
    base_dir: Path
    default_filename: str
    default_values: PresetDict
    components: List[object]

    def __init__(
        self,
        base_dir: os.PathLike,
        default_filename='default.json'
    ) -> None:
        self.base_dir = Path(base_dir)
        self.default_filename = default_filename
        self.default_values = self.load(default_filename)[1]
        self.components = []

    def component(self, component_class: object, **kwargs) -> object:
        # find all the top components from the Gradio context and create a path
        parent = Context.block if HAS_GRADIO else None
        paths = []
        
        # Get label if available
        if 'label' in kwargs:
            paths.append(kwargs['label'])

        while parent is not None:
            if hasattr(parent, 'label'):
                paths.insert(0, parent.label)

            parent = parent.parent if hasattr(parent, 'parent') else None

        path = '/'.join(paths) if paths else "default_path"

        # Create a mock component in standalone mode
        if not HAS_GRADIO:
            component = type('MockComponent', (), {
                'path': path,
                'update': lambda **kw: kw.get('value', None)
            })()
            # Set additional attributes if needed
            for key, value in kwargs.items():
                setattr(component, key, value)
        else:
            component = component_class(**{
                **kwargs,
                **self.default_values.get(path, {})
            })

        component.path = path

        self.components.append(component)
        return component

    def load(self, filename: str) -> Tuple[str, PresetDict]:
        if not filename.endswith('.json'):
            filename += '.json'

        path = self.base_dir.joinpath(sanitize_filename_part(filename))
        configs = {}

        if path.is_file():
            configs = json.loads(path.read_text(encoding='utf-8'))

        return path, configs

    def save(self, filename: str, *values) -> Tuple:
        path, configs = self.load(filename)

        for index, component in enumerate(self.components):
            config = configs.get(component.path, {})
            config['value'] = values[index] if index < len(values) else None

            for attr in ['visible', 'min', 'max', 'step']:
                if hasattr(component, attr):
                    config[attr] = config.get(attr, getattr(component, attr))

            configs[component.path] = config

        self.base_dir.mkdir(0o777, True, True)
        path.write_text(json.dumps(configs, indent=4), encoding='utf-8')

        return 'successfully saved the preset'

    def apply(self, filename: str) -> Tuple:
        values = self.load(filename)[1]
        outputs = []

        for component in self.components:
            config = values.get(component.path, {})

            if 'value' in config and hasattr(component, 'choices'):
                if hasattr(component, 'choices') and config['value'] not in component.choices:
                    config['value'] = None

            # In standalone mode, just return the value
            if not HAS_GRADIO:
                outputs.append(config.get('value', None))
            else:
                outputs.append(component.update(**config))

        return (*outputs, 'successfully loaded the preset')

    def list(self) -> List[str]:
        presets = [
            p.name
            for p in self.base_dir.glob('*.json')
            if p.is_file()
        ]

        if len(presets) < 1:
            presets.append(self.default_filename)

        return presets