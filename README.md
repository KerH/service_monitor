# service_monitor
Monitor services over the network using client-server architecture

## Installation

To run this project, you need to have Python 3.10+ and Poetry installed on your system.
You can install poetry using pip3:
`pip3 install poetry`

Install project dependencies using:
`poetry install`

Activate virtual environment:
`poetry shell`

To setup your PYTHONPATH to include project path, please run:
`export PYTHONPATH=/path/to/project:$PYTHONPATH`

## Client
Client side includes CLI application.
Currently, it has one command `connect` and then it provides an interactive session.

Usage:
`python src/service_monitor/client/client_app.py connect --server-ip [SERVER-IP] --server-port [SERVER-PORT]`

## Server
Server side for monitoring services over the network.
Simple CLI app for running the server, includes `run` command with port and log
file path initialization.

Usage:
`python src/service_monitor/server/server.py run --port 5000 --log-file-path /tmp`