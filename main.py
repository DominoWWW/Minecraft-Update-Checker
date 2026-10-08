from urllib.request import urlopen
from urllib.parse import urlencode
import tomllib
import json
import re

#### Load configuration from config.toml ###
with open("config.toml", "rb") as config_file:
    config = tomllib.load(config_file)

### Color codes for terminal output ###
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
def colored(text, color):
    return f"{color}{text}{RESET}"

### read project list ###
def get_project_list():
    try:
        with open(config.get("check_list_file"), "r") as file:
            list = []
            for line in file.readlines():
                if line and not line.startswith("#"):
                    line = line.replace(" ", "-")
                    list.append(line)

            return list
    except FileNotFoundError:
        print(colored(f"Error: The file '{config.get('check_list_file')}' was not found.", RED))
        exit(1)

### get latest version ###
def get_highest_version(versions):
    best_version = "0.0.0"
    for version in versions:
        if not re.match(r"^(\d+\.\d+(\.\d+)?)?$", version):
            continue

        if tuple(map(int, version.split("."))) > tuple(map(int, best_version.split("."))):
            best_version = version

    return best_version

### Fetch data ###
def fetch_project_search(project_search_term):
    loaders = config.get("loaders", [])
    facets = json.dumps([[f"categories:{loader}" for loader in loaders]])
    
    params = {
        "query": project_search_term,
        "limit": 1,
        "index": "relevance",
        "facets": facets,
    }

    url = f"https://api.modrinth.com/v2/search?{urlencode(params, safe='[]:')}"
    with urlopen(url) as response:
        results = json.load(response).get("hits", [])

    return results[0] if results else None

def fetch_project_data(project_id):
    try:
        with urlopen(f"https://api.modrinth.com/v2/project/{project_id}") as response:
            results = json.load(response)
            return results
    except Exception:
        return None

def fetch_latest_minecraft_version():
    manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    with urlopen(manifest_url) as response:
        manifest = json.load(response)
    return manifest["latest"]["release"]

### main ###
def main():
    # Fetch the latest Minecraft version
    latest_minecraft_version = fetch_latest_minecraft_version()

    # Prompt the user for a Minecraft version
    chosen_version = input(colored(f"Minecraft version ({latest_minecraft_version}): ", GREEN))
    if not re.match(r"^(\d+\.\d+(\.\d+)?)?$", chosen_version):
        print(colored("Invalid version format. Please enter a valid Minecraft version (e.g., 1.20.1).", RED))
        return

    if not chosen_version:
        chosen_version = latest_minecraft_version

    # get the project list
    project_checklist = get_project_list()

    # Fetch project data from modrinth API
    projects = []
    for project_name in project_checklist:
        searched = False
        project = fetch_project_data(project_name)
        if project is None and config.get("use_search_as_backup") == False:
            projects.append(
                {
                    "name": project_name,
                    "id": None,
                    "slug": None,
                    "versions": None,
                    "status": "not found",
                }
            )
            continue

        elif project is None:
            search_project = fetch_project_search(project_name)
            project = fetch_project_data(search_project["project_id"]) if search_project else None
            searched = True
            if project is None:
                projects.append(
                    {
                        "name": project_name,
                        "id": None,
                        "slug": None,
                        "versions": None,
                        "status": "not found",
                    }
                )
                continue

        status = "searched" if searched else "found"

        projects.append(
            {
                "name": project["title"],
                "id": project["id"],
                "slug": project["slug"],
                "version": get_highest_version(project["game_versions"]),
                "status": status
            }
        )

    for project in projects:
        message = ""
        match project["status"]:
            case "not found":
                message = colored(f"✗ {project['name']}: project not found", RED)
            case "found":
                if project["version"] == chosen_version:
                    message = colored(f"✔ {project['name']} ({project['version']}): is updated", GREEN)
                else:
                    message = colored(f"✗ {project['name']} ({chosen_version}): latest version {project['version']}", YELLOW)
            case "searched":
                if project["version"] == chosen_version:
                    message = colored(f"✔ {project['name']} ({project['version']}): is updated - searched", GREEN)
                else:
                    message = colored(f"✗ {project['name']} ({chosen_version}): latest version {project['version']} - searched", YELLOW)

        print(message)
        
        

if __name__ == "__main__":
    main()