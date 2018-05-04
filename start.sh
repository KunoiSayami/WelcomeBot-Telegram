#!/bin/bash
while true; do
	git fetch
	git pull
	git submodule update --init
	python main.py
	sleep 5
done
