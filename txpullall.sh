#!/bin/bash

if [ -n "$1" ]
then
    LOCALE_DIR=$1
else
    LOCALE_DIR="$VIRTUAL_ENV/../localpower/locale"
fi

for f in $(ls $LOCALE_DIR | grep -v pot)
do
    FNAME="${LOCALE_DIR}/${f}/LC_MESSAGES/django.po"
    touch -m -d `grep PO-Revision-Date $FNAME | awk '{print $2, $3}' | awk -F'\\' '{print $1}'` $FNAME
done

tx pull -a
