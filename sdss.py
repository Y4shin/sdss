#!/usr/bin/env python3

# Stow Dotfiles Setup Script (SDSS)
# By Patric Plattner <patric@patricplattner.de>
# License: GNU General Public License v3

# This script manages dotfiles setups using GNU stow. It allows to mix and match
# different dotfiles and handles on the fly switching.

# IMPORTS

import argparse
import sys
import os
import socket

# CONSTANTS

# List of all commands.
# Comprised of list of 4-tuples in format of:
# (short-name, long-name, desc, dest, takes_argument)
commands = [
    ("-c", "--clone", "Clone dotfiles repo into repo folder", "clone_repo", 1),
    ("-a", "--activate-package", "Activate single package out of a repo.", "a_package", 1),
    ("-A", "--activate-repo", "Activate all packages out of a repo.", "a_repo", 1),
    ("-d", "--deactivate-package", "Deactivate singele package out of a repo.", "d_package", 1),
    ("-D", "--deactivate-repo", "Deactivate all packages out of a repo.", "d_repo", 1),
    ("-l", "--list-packages", "Lists all packages in a repo.", "l_repo", 1),
    ("-L", "--list-repos", "Lists all repos.", "l_repos", 0),
    ("-V", "--change-package-version", "Change version of a package. Provide 2 arguments: <package> <version>.", "cv_package", 2),
    (None, "--change-repo-version", "Change version of all packages in a repo. Provide 2 arguments: <repo> <version>.", "cv_repo", 2),
    ("-R", "--refresh", "Refreshes package database.", "refresh", 0),
    ("-v", "--version", "Print version of sdss.", "version", 0)
]

# GLOBAL VARS

SDSS_DATA_DIR = os.getenv("SDSS_DATA_DIR") if os.getenv("SDSS_DATA_DIR") is not None else "{}/.local/share/sdss".format(os.getenv("HOME"))


# HOUSEKEEPING FUNCTIONS

def getargs():
    parser = argparse.ArgumentParser(description="Stow Dotfiles Setup Script (SDSS). Please only provide one command at a time.")
    for command in commands:
        if command[0] is not None:
            if command[4] > 0:
                parser.add_argument(command[0], command[1], help=command[2], dest=command[3], nargs=command[4])
            else:
                parser.add_argument(command[0], command[1], help=command[2], action="store_true", dest=command[3])
        else:
            if command[4] > 0:
                parser.add_argument(command[1], help=command[2], dest=command[3], nargs=command[4])
            else:
                parser.add_argument(command[1], help=command[2], action="store_true", dest=command[3])
    return parser.parse_args()

def get_command(args):
    activated_command = None
    args_dict = vars(args)
    for com in commands:
        command = com[3]
        if args_dict[command] is not None and (args_dict[command] == True or isinstance(args_dict[command], str)):
            if activated_command is None:
                activated_command = (command, args_dict[command])
            else:
                sys.stderr.write("Only provide one command at a time.\n")
                sys.exit(1)
    return activated_command


# COMMAND FUNCTIONS

def refresh():
    #getting current dotfile version
    current_version = "default"
    if not os.path.isfile(os.path.join(SDSS_DATA_DIR, "sdss.conf")):
        with open(os.path.join(SDSS_DATA_DIR, "sdss.conf"), "w") as conffile:
            conffile.write("version={}\n".format(current_version))
    else:
        with open(os.path.join(SDSS_DATA_DIR, "sdss.conf"), "r") as conffile:
            for line in conffile.readlines():
                if line.split("=")[0] == "version":
                    current_version = line.split("=")[1].replace("\n", "")
    #getting all repos, appending full pathname and filtering only directories
    repos = [os.path.join(SDSS_DATA_DIR, "repos", name) for name in os.listdir(os.path.join(SDSS_DATA_DIR, "repos")) if os.path.isdir(os.path.join(SDSS_DATA_DIR, "repos", name))]
    for repo in repos:
        #getting packages of repo, filtering for dotfiles and non-folders
        packages = [os.path.join(repo, name) for name in os.listdir(repo) if os.path.isdir(os.path.join(repo, name)) and name[0] != "."]
        for package in packages:
            #generating initial sdss.data if not existent (aka initializing
            if not os.path.isfile(os.path.join(package, "sdss.data")):
                with open(os.path.join(package, "sdss.data"), "w") as package_data:
                    package_data.write("name={}\nstate=inactive\n".format(
                        package.split("/")[-1]))
                os.mkdir(os.path.join(package, "stash"))
            print(current_version)
            for root, dirs, files in os.walk(os.path.join(package, "data")):
                for entry in dirs+files:
                    if entry[-5:] == ":sdss":
                        with open(os.path.join(package, "sdss.data"), "a+") as package_data:
                            if entry.split(":")[-2] == current_version:
                                print("initial deploy: "+os.path.join(root,entry))
                                package_data.write("alt:{}:active={}\n".format(
                                    current_version,
                                    os.path.join(root, entry.split(":")[0])))
                                os.rename(os.path.join(root, entry), os.path.join(root, entry.split(":")[0]))
                            else:
                                print("initial stash: "+os.path.join(root,entry))
                                stash_id=max([int(a) for a in os.listdir(os.path.join(package, "stash"))] + [0]) + 1
                                package_data.write("alt:{}:{}={}\n".format(
                                    entry.split(":")[-2],
                                    stash_id,
                                    os.path.join(root, entry.split(":")[0])))
                                os.rename(os.path.join(root, entry), os.path.join(package, "stash", str(stash_id)))
            new_lines = []
            tmp_files = []
            with open(os.path.join(package, "sdss.data"), "r") as package_data:
                for line in package_data.readlines():
                    key = line.split("=")[0]
                    data = line.split("=")[1].replace("\n", "")
                    if key.split(":")[0] == "alt":
                        #version does not match -> move to stash
                        if key.split(":")[1] != current_version:
                            #still active -> move to stash
                            if key.split(":")[2] == "active":
                                print("stash afterwards: " + data + ":" + key.split(":")[1])
                                stash_id=max([int(a) for a in os.listdir(os.path.join(package, "stash"))] + [0]) + 1
                                os.rename(data, os.path.join(package, "stash", str(stash_id)))
                                new_lines.append(key.split(":")[0] + ":" + key.split(":")[1] + ":" + str(stash_id) + "=" + data)
                            #in stash -> no action required
                            else:
                                print("keep stashed: " + data + ":" + key.split(":")[1])
                                new_lines.append(line)
                        #version does match -> move to active
                        else:
                            #still inactive -> activate
                            if key.split(":")[2] != "active":
                                print("deploy afterwards: " + data + ":" + key.split(":")[1])
                                if os.path.isfile(data):
                                    os.rename(os.path.join(package, "stash", key.split(":")[2]), data+":tmp")
                                    tmp_files.append(data+":tmp")
                                else:
                                    os.rename(os.path.join(package, "stash", key.split(":")[2]), data)
                                new_lines.append(key.split(":")[0] + ":" + key.split(":")[1] + ":active" + "=" + data)
                            #already active -> no action required
                            else:
                                print("keep deployed: " + data + ":" + key.split(":")[1])
                                new_lines.append(line)

                    else:
                        new_lines.append(line)
            for tmp_file in tmp_files:
                os.rename(tmp_file, tmp_file[:-4])
            with open(os.path.join(package, "sdss.data"), "w") as wfile:
                for line in new_lines:
                    wfile.write(line)
                    if line[-1] != "\n":
                        wfile.write("\n")
def clone(arg):
    print("Clone not yet implemented.")

def activate_package(arg):
    print("Activate Package not yet implemented")

def activate_repo(arg):
    print("Activate Repo not yet implemented")

def deactivate_package(arg):
    print("Deactivate Package not yet implemented")

def deactivate_repo(arg):
    print("Deactivate Repo not yet implemented")

def list_packages(arg):
    print("List Packages not yet implemented")

def list_repos():
    print("List Repos not yet implemented")

def version(arg):
    print("Version not yet implemented")



if __name__ == "__main__":
    comm = get_command(getargs())
    if comm is None:
        sys.stderr.write("Please provide a command.")
        sys.exit(1)
    command, arg = comm
    if command == "refresh":
        refresh()
    elif command == "clone":
        clone(arg)
    elif command == "a_package":
        activate_package(arg)
    elif command == "a_repo":
        activate_repo(arg)
    elif command == "d_package":
        deactivate_package(arg)
    elif command == "d_repo":
        deactivate_repo(arg)
    elif command == "l_repo":
        list_packages(arg)
    elif command == "l_repos":
        list_repos()
    elif command == "version":
        version()
