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
import shutil
import errno

# CONSTANTS

# List of all commands.
# Comprised of list of 4-tuples in format of:
# (short-name, long-name, desc, dest, takes_argument)
commands = [
    ("-c", "--clone", "Clone dotfiles repo into repo folder", "clone_repo", 1),
    ("-a", "--activate-package", "Activate single package out of a repo. Provide 2 arguments: <repo> <package>.", "a_package", 2),
    ("-A", "--activate-repo", "Activate all packages out of a repo.", "a_repo", 1),
    ("-d", "--deactivate-package", "Deactivate singele package out of a repo. Provide 2 arguments: <repo> <package>.", "d_package", 2),
    ("-D", "--deactivate-repo", "Deactivate all packages out of a repo.", "d_repo", 1),
    ("-l", "--list-packages", "Lists all packages in a repo.", "l_repo", 1),
    ("-L", "--list-repos", "Lists all repos.", "l_repos", 0),
    ("-V", "--change-version", "Change version of a package.", "change_version", 1),
    ("-e", "--toggle-edit-mode", "Toggle edit mode.", "toggle:edit", 0),
    ("-R", "--refresh", "Refreshes package database.", "refresh", 0),
    ("-v", "--print-version", "Print version of sdss.", "version", 0)
]

# GLOBAL VARS

SDSS_DATA_DIR = os.getenv("SDSS_DATA_DIR") if os.getenv("SDSS_DATA_DIR") is not None else "{}/.local/share/sdss".format(os.getenv("HOME"))
SDSS_DEST_DIR = os.getenv("SDSS_DEST_DIR") if os.getenv("SDSS_DEST_DIR") is not None else os.getenv("HOME")
SDSS_VERSION  = "0.1"
SDSS_EDIT_DIR = os.getenv("SDSS_EDIT_DIR") if os.getenv("SDSS_EDIT_DIR") is not None else "{}/dotfiles".format(os.getenv("HOME"))


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
        if args_dict[command] is not None and (args_dict[command] == True or isinstance(args_dict[command], str) or isinstance(args_dict[command], list)):
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
            conffile.write("version={},edit=inactive\n".format(current_version))
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
            try:
                os.mkdir(os.path.join(package, "deploy"))
            except FileExistsError:
                pass
            #walking over all data files and add sdss.data entries.
            known_files = []
            with open(os.path.join(package, "sdss.data"), "r") as package_data:
                for line in package_data.readlines():
                    key = line.split("=")[0]
                    data = line.split("=")[1]
                    if key == "file" or key == "dir":
                        known_files.append(data[:-1])
                    elif key[:3] == "alt":
                        known_files.append(data[:-1]+".{}.sdss".format(key.split(".")[1]))
            for root, dirs, files in os.walk(os.path.join(package, "data")):
                for entry in dirs+files:
                    #do not add duplicate entries
                    if os.path.join(root, entry) in known_files:
                        continue
                    #add dir entry to sdss.data
                    if os.path.isdir(os.path.join(root, entry)):
                        with open(os.path.join(package, "sdss.data"), "a+") as package_data:
                            package_data.write("dir={}\n".format(os.path.join(root, entry)))
                    #handle versioned file.
                    elif entry[-5:] == ".sdss":
                        with open(os.path.join(package, "sdss.data"), "a+") as package_data:
                            #determine if version is supposed to be active and write to sdss.data accordingly
                            if entry.split(".")[-2] == current_version:
                                package_data.write("alt.{}.active={}\n".format(
                                    current_version,
                                    os.path.join(root, entry.split(".")[0])))
                            else:
                                package_data.write("alt.{}.inactive={}\n".format(
                                    entry.split(".")[-2],
                                    os.path.join(root, entry.split(".")[0])))
                    #add regular file to sdss.data
                    else:
                        with open(os.path.join(package, "sdss.data"), "a+") as package_data:
                            package_data.write("file={}\n".format(os.path.join(root, entry)))
            #reading lines from sdss.data and filling them into new_lines with needed changes
            new_lines = []
            #if file already exists, then old version is still in place and if
            #it is overwritten now, the new file will be deleted when the
            #overwritten file will be handled, so they will be saved as XXX.tmp
            #and renamed once all files were handled.
            tmp_files = []
            #if already active, then it will be restowed so changes are
            #propagated to SDSS_DEST_DIR
            restow = False
            #ugly hack to prevent python weirdness of not copying anything
            #while in `with open(...) as file` block.
            cpyqueue = []
            with open(os.path.join(package, "sdss.data"), "r") as package_data:
                for line in package_data.readlines():
                    key = line.split("=")[0]
                    data = line.split("=")[1].replace("\n", "")
                    #handle versioned file
                    if key.split(".")[0] == "alt":
                        if not os.path.isfile(data+".{}.sdss".format(key.split(".")[1])):
                            continue
                        #disable versioned file if version does not match anymore
                        if key.split(".")[1] != current_version:
                            if os.path.isfile(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1)):
                                os.remove(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1))
                            new_lines.append(key.split(".")[0] + "." + key.split(".")[1] + ".inactive=" + data)
                        #reenable if version matches again
                        else:
                            #see comment on `tmp_files = []`
                            if os.path.isfile(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1)):
                                #this hack is ugly as hell, but it won't copy otherwise.
                                cpyqueue.append(("{}.{}.sdss".format(data, key.split(".")[1]), "{}..tmp".format(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1))))
                                tmp_files.append(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1)+"..tmp")
                            else:
                                src=data + ".{}.sdss".format(key.split(".")[1])
                                dst=data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1)
                                cpyqueue.append((src, dst))
                            new_lines.append(key.split(".")[0] + "." + key.split(".")[1] + ".active" + "=" + data)
                    #handle directory
                    elif key == "dir":
                        if os.path.isfile(data):
                            shutil.rmtree(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1))
                            cpyqueue.append((data, data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1)))
                            new_lines.append("file="+line.split("=")[1])
                        elif not os.path.isdir(data):
                            shutil.rmtree(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1))
                        else:
                            try:
                                os.mkdir(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1))
                            except FileExistsError:
                                pass
                            new_lines.append(line)
                    #handle file
                    elif key == "file":
                        if os.path.isdir(data):
                            os.remove(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1))
                            os.mkdir(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1))
                            new_lines.append("dir="+line.split("=")[1])
                        elif not os.path.isfile(data):
                            try:
                                os.remove(data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1))
                            except FileNotFoundError:
                                pass
                        else:
                            src=data
                            dst=data.replace(os.path.join(package, "data"), os.path.join(package, "deploy"), 1)
                            cpyqueue.append((src, dst))
                            new_lines.append(line)
                    #check whether restow is needed
                    elif key == "state":
                        if data == "active":
                            restow = True
                        new_lines.append(line)
            #actually copy stuff
            for cmd in cpyqueue:
                shutil.copy2(cmd[0], cmd[1])
            #undo XXX.tmp workaround
            for tmp_file in tmp_files:
                os.rename(tmp_file, tmp_file[:-5])
            #write changes to active file
            with open(os.path.join(package, "sdss.data"), "w") as wfile:
                for line in new_lines:
                    wfile.write(line)
                    if line[-1] != "\n":
                        wfile.write("\n")
            if restow:
                success = os.system("stow -S {} -d {} -t {} >/dev/null 2>&1".format("data", package_dir, SDSS_DEST_DIR))

def clone(arg):
    os.chdir(os.path.join(SDSS_DATA_DIR, "repos"))
    if os.system("git clone {}".format(arg[0])) == 0:
        print("Successfully cloned repo. Please refresh to initialize the repo for use.")
    else:
        print("Could not clone repo.")

def activate_package(arg):
    package_dir = os.path.join(SDSS_DATA_DIR, "repos", arg[0], arg[1])
    success=False
    with open(os.path.join(package_dir, "sdss.data"), "r") as config_file:
        #check if active
        if [line for line in config_file.readlines() if line.split("=")[0] == "state"][0].split("=")[1][:-1] == "inactive":
            success = os.system("stow -S {} -d {} -t {}".format("deploy", package_dir, SDSS_DEST_DIR)) == 0
    if success:
        text = ""
        with open(os.path.join(package_dir, "sdss.data"), "r") as config_file:
            text = config_file.read().replace("state=inactive", "state=active")
        with open(os.path.join(package_dir, "sdss.data"), "w") as config_file:
            config_file.write(text)
        print("Package {}/{} successfully activated.".format(arg[0], arg[1]))
    else:
        print("Package {}/{} failed to activate.".format(arg[0], arg[1]))

def activate_repo(arg):
    for package in [pkg for pkg in os.listdir(os.path.join(SDSS_DATA_DIR, "repos", arg[0])) if os.path.isdir(os.path.join(SDSS_DATA_DIR, "repos", arg[0], pkg)) and pkg[0] != "."]:
        activate_package([arg[0], package])

def deactivate_package(arg):
    package_dir = os.path.join(SDSS_DATA_DIR, "repos", arg[0], arg[1])
    success=False
    with open(os.path.join(package_dir, "sdss.data"), "r") as config_file:
        #check if active
        if [line for line in config_file.readlines() if line.split("=")[0] == "state"][0].split("=")[1][:-1] == "active":
            success = os.system("stow -D {} -d {} -t {}".format("deploy", package_dir, SDSS_DEST_DIR)) == 0
    if success:
        text = ""
        with open(os.path.join(package_dir, "sdss.data"), "r") as config_file:
            text = config_file.read().replace("state=active", "state=inactive")
        with open(os.path.join(package_dir, "sdss.data"), "w") as config_file:
            config_file.write(text)
        print("Package {}/{} successfully deactivated.".format(arg[0], arg[1]))
    else:
        print("Package {}/{} failed to deactivate.".format(arg[0], arg[1]))

def deactivate_repo(arg):
    for package in [pkg for pkg in os.listdir(os.path.join(SDSS_DATA_DIR, "repos", arg[0])) if os.path.isdir(os.path.join(SDSS_DATA_DIR, "repos", arg[0], pkg)) and pkg[0] != "."]:
        deactivate_package([arg[0], package])

def list_packages(arg):
    for package in [pkg for pkg in os.listdir(os.path.join(SDSS_DATA_DIR, "repos", arg[0])) if os.path.isdir(os.path.join(SDSS_DATA_DIR, "repos", arg[0], pkg)) and pkg[0] != "."]:
        print(package)

def list_repos():
    for repo in [pkg for pkg in os.listdir(os.path.join(SDSS_DATA_DIR, "repos")) if os.path.isdir(os.path.join(SDSS_DATA_DIR, "repos", arg[0], pkg)) and pkg[0] != "."]:
        print(repo)

def version(arg):
    print("sdss {}".format(SDSS_VERSION))

def change_version(arg):
    print("Change Package Version not yet implemented")

if __name__ == "__main__":
    args = getargs()
    comm = get_command(args)
    if comm is None:
        sys.stderr.write("Please provide a command.")
        sys.exit(1)
    command, arg = comm
    if command == "refresh":
        refresh()
    elif command == "clone_repo":
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
    elif command == "change_version":
        change_version(arg)
    elif command == "toggle_edit":
        toggle_edit()
