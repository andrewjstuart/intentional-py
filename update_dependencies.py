import subprocess
import tomllib

""" Reads the TOML file to find dependencies and updates them (remove and add) in the TOML file using uv."""

with open("pyproject.toml", mode="rb") as fp:
    pyproject = tomllib.load(fp)
    for key in pyproject.keys():
        if key == "project":
            for project_key in pyproject[key].keys():
                if project_key == "dependencies":
                    for dep in pyproject[key][project_key]:
                        dependency_list: list = dep.split(">=", maxsplit=2)
                        remove = subprocess.run(["uv", "remove", dependency_list[0]])
                        add = subprocess.run(["uv", "add", dependency_list[0]])

lock_upgrade = subprocess.run(["uv", "lock", "--upgrade"])
487045
