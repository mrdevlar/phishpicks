from __future__ import annotations
import random
import subprocess
import shlex
from pathlib import Path


# @TODO: Configuration of winamp and phish_folder, command line interface
# @TODO: Pull/Push configuration from os.path.expanduser('~/.phishpicks/') see 20240416-10-40-21

def main():
    winamp = Path("C:\Program Files (x86)\Winamp\winamp.exe")
    phish_folder = Path("Z:\Music\Phish")

    possible_folders = [folder for folder in phish_folder.glob("Phish [0-9]*")]
    selected_folder = random.choice(possible_folders)
    print(selected_folder)
    enqueue = False
    enqueue_command = "/ADD " if enqueue else ""

    cmd = 'powershell -Command' + f"""& "{winamp}" {enqueue_command}"{selected_folder}" """
    print(cmd)

    args = shlex.split(cmd)
    process = subprocess.Popen(args,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               stdin=subprocess.PIPE,
                               shell=True)  # Create subprocess
    # stdout, stderr = process.communicate(input=b'y\n')  # Run command and send input, then read output
    # process.terminate()
    # print(stdout)  # Print output
    # print(stderr)  # Print error output, if any


if __name__ == '__main__':
    main()
