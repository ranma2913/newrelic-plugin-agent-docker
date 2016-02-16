
from newrelic_plugin_agent import agent
from newrelic_plugin_agent import plugins as original_plugins
from glob import glob
import os

def import_module(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

if __name__ == "__main__":
    for plugin in glob("plugins/*.py"):
        full_path, _ = os.path.splitext(plugin)
        filename = os.path.basename(full_path)
        if filename.startswith("__"):
            continue
        mod = import_module(full_path.replace("/","."))
        plugin_class = mod.__dict__.get(filename.title())
        print(plugin_class)
        if not plugin_class:
            continue
        original_plugins.available.update({filename: ".".join([plugin_class.__module__, filename.title()])})
    agent.main()
