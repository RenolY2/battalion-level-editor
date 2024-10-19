import configparser


def read_config():
    print("reading")
    cfg = configparser.ConfigParser()
    with open("editor_config.ini", "r") as f:
        cfg.read_file(f)
    print("read")
    return cfg


def make_default_config():
    cfg = configparser.ConfigParser()

    cfg["default paths"] = {
        "xml": ""
    }

    cfg["editor"] = {
        "InvertZoom": "False",
        "wasdscrolling_speed": "125",
        "wasdscrolling_speedupfactor": "5",
        "3d_background": "255 255 255",
        "regenerate_pf2": "True",
        "regenerate_waypoints": "False",
        "fps_counter": "False",
        "dark_mode": "True"
    }

    with open("editor_config.ini", "w") as f:
        cfg.write(f)

    return cfg


def save_cfg(cfg):
    with open("editor_config.ini", "w") as f:
        cfg.write(f)