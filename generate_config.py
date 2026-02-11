import json
import shutil


def main():
    shutil.copyfile("config_template.json", "config_template.json")
    print("generated config_template.json")


if __name__ == "__main__":
    main()
