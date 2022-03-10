################################################
#                                              #
#  Because I'm too lazy to delete each thing   #
#                                              #
#            Author: Sam Bailey                #
#        Last Revised: Mar 07, 2022            #
#                                              #
#          Created on Mar 07, 2022             #
#                                              #
################################################

import os
import sys
import contextlib

mode = input("> Would you like to use clean mode or delete mode? ")

if mode == 'delete':
    path = input("> Type the filepath of the directory you would like to delete: ")
elif mode == 'clean':
    path = input("> Type the filepath of the directory you would like to clean: ")
else:
    sys.exit("<!> That is not a valid mode <!>")

if os.path.isdir(path):
    if mode == 'delete':
        confirm = input(f"> Are you sure you'd like to delete {path} and all its contents? ")
    else:
        confirm = input(f"> Are you sure you'd like to delete all of {path}'s contents? ")
    if confirm != 'y':
        sys.exit("<!> Process terminated <!>")
else:
    sys.exit("<!> That is not a valid directory <!>")

def clear(inPath):
    for subPath in os.listdir(inPath):
#        if subPath.startswith("."):
#            os.system(f"rm -rf {inPath}/{subPath}")
        if os.path.isdir(f"{inPath}/{subPath}"):
            clear(f"{inPath}/{subPath}")
            os.rmdir(f"{inPath}/{subPath}")
        else:
            with contextlib.suppress(FileNotFoundError):
                os.remove(f"{inPath}/{subPath}")
            

clear(path)

if mode == 'delete':
    os.rmdir(path)