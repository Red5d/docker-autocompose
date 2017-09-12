# docker-autocompose
Generates a docker-compose yaml definition from a running container.

Required Modules:
* [pyaml](https://pypi.python.org/pypi/pyaml/)
* [docker-py](https://pypi.python.org/pypi/docker-py)

Example Usage:

    sudo python autocompose.py container-name

Outputs a docker-compose compatible yaml structure.
[docker-compose reference](https://docs.docker.com/compose/)
[docker-compose yaml file specification](https://docs.docker.com/compose/compose-file/)

While experimenting with various docker containers from the Hub, I realized that I'd started several containers with complex options for volumes, ports, environment variables, etc. and there was no way I could remember all those commands without referencing the Hub page for each image if I needed to delete and re-create the container (for updates, or if something broke).

With this tool, I can easily generate docker-compose files for managing the containers that I've set up manually.

## Docker Usage

Build container by running:

    docker build -t docker-autocompose .

Use the new image to generate a docker-compose file from a running container:

     docker run -v /var/run/docker.sock:/var/run/docker.sock docker-autocompose $container-id
