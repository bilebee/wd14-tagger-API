"""Settings for the tagger module in standalone mode"""
import os
from typing import List

# Always in standalone mode
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
    """Called when the UI settings tab is opened - not used in standalone mode"""
    pass
