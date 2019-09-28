#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

day=$(date +"%u")

((!$#)) && echo No arguments supplied! && exit 1

echo "Will schedule the following command (test before running):"
echo "(cd \"$DIR\"; ./gen.py $@)"

read  -n 1 -p "Have you tried test email (y|n)? " hastested

if [ $hastested != "y" ]; then
  echo "Aborting..."
  exit 1
fi

# schedule only on Saturday/Sunday; for the next week
if ((day > 5)); then
  echo "(cd \"$DIR\"; ./gen.py $@ -s 'WILL SPAM SOON: ')" | at 1pm Monday
  echo "(cd \"$DIR\"; ./gen.py $@ send)" | at 2pm Monday
fi

if ((day > 5 || day < 3)); then
  echo "(cd \"$DIR\"; ./gen.py -s 'WILL SPAM SOON: ' $@)" | at 9am Wednesday
  echo "(cd \"$DIR\"; ./gen.py -s 'Reminder: ' $@ send)" | at 10am Wednesday
fi

if ((day != 5)); then
  echo "(cd \"$DIR\"; ./gen.py -s 'WILL SPAM SOON: ' $@)" | at 9am Friday
  echo "(cd \"$DIR\"; ./gen.py -s 'Reminder: ' $@ send)" | at 10am Friday
  echo "(cd \"$DIR\"; ./gen.py -s 'STARTING NOW: ' $@ send)" | at 1:55pm Friday
fi

