#!/bin/bash

FILES=_YOUR_PATH_/loader/taggedtext_split_*
tmux start-server
for f in $FILES
do
   windowName="bioe-${f: -2}"
   echo $windowName
   tmux kill-session -t ${windowName}
done
