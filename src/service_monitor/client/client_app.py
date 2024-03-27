"""Client cli application to monitor network services."""

import sys
from datetime import datetime

import click
from munch import Munch

from client import (
    Client,
    ClientConnectionException,
    ClientServiceRegistrationException,
    ClientSetOutageTimeException,
    ClientSetGraceTimeException,
)


def _register_service(client: Client):
    """Register a new service to monitor on.

    Args:
        client(Client): client object to interact with the server
    """
    service_info = click.prompt(
        "Please enter service host and port,"
        "and poll frequency for it, seperated by space"
        "(e.g. 127.0.0.1 5000 3)"
    )
    host, port, poll_freq = service_info.split()
    try:
        client.register_service(host, port, poll_freq)
    except ClientServiceRegistrationException as err:
        click.echo(f"Error occurred while registering service. {err}")


def _convert_str_to_tuple_datetime(_date: str, _time: str):
    """Convert given date and time from string to datetime format.

    Args:
        _date(str): date in string format YYYY-MM-DD
        _time(str): time in string format HH:MM:SS

    Return:
        datetime: representing given date and time
    """
    year, month, day = [int(x) for x in _date.split("-")]
    hour, minute, second = [int(x) for x in _time.split(":")]

    return datetime(year, month, day, hour, minute, second)


def _set_outage_time(client: Client):
    """Set outage time for given client's service.

    Args:
        client(Client): client object to interact with the server
    """
    outage_info = click.prompt(
        "Please enter service(host, port) and service outage "
        "time (start time and end time) separated by space.\n"
        "Format: host port "
        "YYYY-MM-DD HH:MM:SS YYYY-MM-DD HH:MM:SS"
    )
    host, port, start_date, start_time, end_date, end_time = outage_info.split()
    s_time_tuple = _convert_str_to_tuple_datetime(start_date, start_time)
    e_time_tuple = _convert_str_to_tuple_datetime(end_date, end_time)
    try:
        client.register_service_outage(host, port, s_time_tuple, e_time_tuple)
    except ClientSetOutageTimeException as err:
        click.echo(f"Error occurred while setting outage time. {err}")


def _set_grace_time(client: Client):
    """Set client grace time for all services.

    Args:
        client(Client): client object to interact with the server
    """
    gt = click.prompt("Please enter grace time in seconds", type=int)
    try:
        client.register_grace_time(gt)
    except ClientSetGraceTimeException as err:
        click.echo(f"Error occurred while setting grace time. {err}")


def _exit(client: Client, err_code: int = 0):
    """Release client's resources and exit."""
    client.cleanup()
    sys.exit(err_code)


# cli app handlers for each command
handlers = Munch(
    register_service=_register_service,
    set_outage_time=_set_outage_time,
    set_grace_time=_set_grace_time,
    exit_app=_exit,
)


@click.group
def cli():
    pass


@cli.command(help="Connect client to monitor server")
@click.option(
    "--server-ip", required=True, type=str, help="monitoring server IP"
)
@click.option(
    "--server-port", required=True, type=int, help="monitoring server port"
)
def connect(server_ip: str, server_port: int):
    try:
        click.echo("Connecting to server...")
        client = Client(server_ip, server_port)
        click.echo("Connection established successfully")
        while True:
            cmd = click.prompt(
                "Please enter next command",
                type=click.Choice(
                    [
                        "register_service",
                        "set_outage_time",
                        "set_grace_time",
                        "exit_app",
                    ]
                ),
            )
            handlers.get(cmd)(client)

    except KeyboardInterrupt:
        click.echo("Shutting down client...")
        _exit(client)

    except ClientConnectionException as err:
        click.echo(
            "Can not connect to server." f"The following error occured: {err}"
        )
        _exit(client, err_code=1)

    except Exception as err:
        click.echo(f"Error occured during operation. {err}")
        _exit(client, err_code=1)


if __name__ == "__main__":
    cli()
