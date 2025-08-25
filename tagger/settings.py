"""Settings tab entries for the tagger module"""
import os
from typing import List

try:
    from modules import shared  # pylint: disable=import-error
    HAS_SD = True
except ImportError:
    HAS_SD = False
    # Create a mock shared object for standalone mode
    class MockOpts:
        def __init__(self):
            self.options = {}
            
        def add_option(self, key, info):
            self.options[key] = info
            
        def onchange(self, key, func):
            pass
            
        def get(self, key, default=None):
            opt = self.options.get(key)
            if opt and hasattr(opt, 'default'):
                return opt.default
            return default
    
    class MockOptionInfo:
        def __init__(self, default, label, section=None, component=None, component_args=None):
            self.default = default
            self.label = label
            self.section = section
            self.component = component
            self.component_args = component_args
    
    class MockShared:
        def __init__(self):
            self.opts = MockOpts()
            self.models_path = os.path.join(os.getcwd(), "models")
    
    shared = MockShared()
    shared.OptionInfo = MockOptionInfo

import gradio as gr

# kaomoji from WD 1.4 tagger csv. thanks, Meow-San#5400!
DEFAULT_KAMOJIS = '0_0, (o)_(o), +_+, +_-, ._., <o>_<o>, <|>_<|>, =_=, >_<, 3_3, 6_9, >_o, @_@, ^_^, o_o, u_u, x_x, |_|, ||_||'  # pylint: disable=line-too-long # noqa: E501

DEFAULT_OFF = '[name].[output_extension]'

HF_CACHE = os.environ.get('HF_HOME', os.environ.get('HUGGINGFACE_HUB_CACHE',
           str(os.path.join(shared.models_path, 'interrogators'))))

def slider_wrapper(value, elem_id, **kwargs):
    # required or else gradio will throw errors
    return gr.Slider(**kwargs)


class InterrogatorSettings:
    """ Interrogator settings """
    @staticmethod
    def set_output_filename_format():
        """ Set output filename format """
        pass

    @staticmethod
    def format():
        """ Format settings """
        pass

    @staticmethod
    def threshold():
        """ Threshold settings """
        pass

    @staticmethod
    def save_tags():
        """ Save tags settings """
        pass

    @staticmethod
    def batch():
        """ Batch settings """
        pass

    @staticmethod
    def tag_counts():
        """ Tag counts settings """
        pass

    @staticmethod
    def unload():
        """ Unload settings """
        pass

    @staticmethod
    def split_escape(input_str: str, separator: str = ",") -> List[str]:
        """ Split and escape """
        return [x.strip() for x in input_str.split(separator) if x] if input_str else []


def on_ui_settings():
    """Called when the UI settings tab is opened"""
    Its = InterrogatorSettings
    section = 'tagger', 'Tagger'
    shared.opts.add_option(
        key='tagger_out_filename_fmt',
        info=shared.OptionInfo(
            DEFAULT_OFF,
            label='Tag file output format. Leave blank to use same filename or'
            ' e.g. "[name].[hash:sha1].[output_extension]". Also allowed are '
            '[extension] or any other [hash:<algorithm>] supported by hashlib',
            section=section,
        ),
    )
    shared.opts.onchange(
        key='tagger_out_filename_fmt',
        func=Its.set_output_filename_format
    )
    shared.opts.add_option(
        key='tagger_count_threshold',
        info=shared.OptionInfo(
            100.0,
            label="Maximum number of tags to be shown in the UI",
            section=section,
            component=slider_wrapper,
            component_args={"minimum": 1.0, "maximum": 500.0, "step": 1.0},
        ),
    )
    shared.opts.add_option(
        key='tagger_batch_recursive',
        info=shared.OptionInfo(
            True,
            label='Glob recursively with input directory pattern',
            section=section,
        ),
    )
    shared.opts.add_option(
        key='tagger_auto_serde_json',
        info=shared.OptionInfo(
            True,
            label='Auto load and save JSON database',
            section=section,
        ),
    )
    shared.opts.add_option(
        key='tagger_store_images',
        info=shared.OptionInfo(
            False,
            label='Store images in database',
            section=section,
        ),
    )
    shared.opts.add_option(
        key='tagger_weighted_tags_files',
        info=shared.OptionInfo(
            False,
            label='Write weights to tags files',
            section=section,
        ),
    )
    shared.opts.add_option(
        key='tagger_verbose',
        info=shared.OptionInfo(
            False,
            label='Console log tag counts per file, no progress bar',
            section=section,
        ),
    )
    shared.opts.add_option(
        key='tagger_repl_us',
        info=shared.OptionInfo(
            False,
            label='Replace underscores with spaces in tags',
            section=section,
        ),
    )
    shared.opts.add_option(
        key='tagger_escape',
        info=shared.OptionInfo(
            False,
            label='Escape brackets in tags',
            section=section,
        ),
    )
