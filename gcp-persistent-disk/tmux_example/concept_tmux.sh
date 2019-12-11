#!/bin/bash

FILES=YOUR_PATH/loader/conc_split_*
tmux start-server
for f in $FILES
do
   windowName="conc-${f: -2}"
   echo $windowName
   tmux new-session -d -s ${windowName}
   tmux send-keys -t ${windowName} "source ~/library-beam/venv_elastic/bin/activate" Enter
   #Add the dns_name here. Todo: improve it.
   tmux send-keys -t ${windowName} "export HOST=......" Enter
   tmux send-keys -t ${windowName} "export input=${f}; ./es_concept.sh" Enter
done
