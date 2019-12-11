#!/bin/bash

FILES=_YOUR_PATH/loader/publ_split_*
tmux start-server
for f in $FILES
do
   windowName="publ-${f: -2}"
   echo $windowName
   tmux kill-session -t ${windowName}
done
