import yaml


def get_config(path):
    with open(path) as f:
        config = yaml.safe_load(f)
    return config
