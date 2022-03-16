#! /usr/bin/env python
import datetime
import sys, argparse, pyaml, docker
from collections import OrderedDict

def main():
    parser = argparse.ArgumentParser(description='Generate docker-compose yaml definition from running container.')
    parser.add_argument('-v', '--version', type=int, default=3, help='Compose file version (1 or 3)') 
    parser.add_argument('cnames', nargs='*', type=str, help='The name of the container to process.')
    args = parser.parse_args()

    struct = {}
    networks = {}
    for cname in args.cnames:
        cfile, c_networks = generate(cname)

        struct.update(cfile)
        networks.update(c_networks)

    render(struct, args, networks)


def render(struct, args, networks):
    # Render yaml file
    if args.version == 1:
        pyaml.p(OrderedDict(struct))
    else:
        pyaml.p(OrderedDict({'version': '"3"', 'services': struct, 'networks': networks}))


def is_date_or_time(s: str):
    for parse_func in [datetime.date.fromisoformat, datetime.datetime.fromisoformat]:
        try:
            parse_func(s.rstrip('Z'))
            return True
        except ValueError:
            pass
    return False


def fix_label(label: str):
    return f"'{label}'" if is_date_or_time(label) else label


def generate(cname):
    c = docker.from_env()

    try:
        cid = [x.short_id for x in c.containers.list(all=True) if cname == x.name or x.short_id in cname][0]
    except IndexError:
        print("That container is not available.", file=sys.stderr)
        sys.exit(1)

    cattrs = c.containers.get(cid).attrs


    # Build yaml dict structure

    cfile = {}
    cfile[cattrs['Name'][1:]] = {}
    ct = cfile[cattrs['Name'][1:]]

    values = {
        'cap_add': cattrs['HostConfig']['CapAdd'],
        'cap_drop': cattrs['HostConfig']['CapDrop'],
        'cgroup_parent': cattrs['HostConfig']['CgroupParent'],
        'container_name': cattrs['Name'][1:],
        'devices': [],
        'dns': cattrs['HostConfig']['Dns'],
        'dns_search': cattrs['HostConfig']['DnsSearch'],
        'environment': cattrs['Config']['Env'],
        'extra_hosts': cattrs['HostConfig']['ExtraHosts'],
        'image': cattrs['Config']['Image'],
        'labels': {label: fix_label(value) for label, value in cattrs['Config']['Labels'].items()},
        'links': cattrs['HostConfig']['Links'],
        #'log_driver': cattrs['HostConfig']['LogConfig']['Type'],
        #'log_opt': cattrs['HostConfig']['LogConfig']['Config'],
        'logging': {'driver': cattrs['HostConfig']['LogConfig']['Type'], 'options': cattrs['HostConfig']['LogConfig']['Config']},
        'networks': {x for x in cattrs['NetworkSettings']['Networks'].keys() if x != 'bridge'},
        'security_opt': cattrs['HostConfig']['SecurityOpt'],
        'ulimits': cattrs['HostConfig']['Ulimits'],
        'volumes': cattrs['HostConfig']['Binds'],
        'volume_driver': cattrs['HostConfig']['VolumeDriver'],
        'volumes_from': cattrs['HostConfig']['VolumesFrom'],
        'entrypoint': cattrs['Config']['Entrypoint'],
        'user': cattrs['Config']['User'],
        'working_dir': cattrs['Config']['WorkingDir'],
        'domainname': cattrs['Config']['Domainname'],
        'hostname': cattrs['Config']['Hostname'],
        'ipc': cattrs['HostConfig']['IpcMode'],
        'mac_address': cattrs['NetworkSettings']['MacAddress'],
        'privileged': cattrs['HostConfig']['Privileged'],
        'restart': cattrs['HostConfig']['RestartPolicy']['Name'],
        'read_only': cattrs['HostConfig']['ReadonlyRootfs'],
        'stdin_open': cattrs['Config']['OpenStdin'],
        'tty': cattrs['Config']['Tty']
    }

    # Populate devices key if device values are present
    if cattrs['HostConfig']['Devices']:
        values['devices'] = [x['PathOnHost']+':'+x['PathInContainer'] for x in cattrs['HostConfig']['Devices']]
    
    networks = {}
    if values['networks'] == set():
        del values['networks']
    else:
        networklist = c.networks.list()
        for network in networklist:
            if network.attrs['Name'] in values['networks']:
                networks[network.attrs['Name']] = {'external': (not network.attrs['Internal']),
                                                   'name': network.attrs['Name']}

    # Check for command and add it if present.
    if cattrs['Config']['Cmd'] is not None:
        values['command'] = cattrs['Config']['Cmd']

    # Check for exposed/bound ports and add them if needed.
    try:
        expose_value = list(cattrs['Config']['ExposedPorts'].keys())
        ports_value = [cattrs['HostConfig']['PortBindings'][key][0]['HostIp']+':'+cattrs['HostConfig']['PortBindings'][key][0]['HostPort']+':'+key for key in cattrs['HostConfig']['PortBindings']]

        # If bound ports found, don't use the 'expose' value.
        if (ports_value != None) and (ports_value != "") and (ports_value != []) and (ports_value != 'null') and (ports_value != {}) and (ports_value != "default") and (ports_value != 0) and (ports_value != ",") and (ports_value != "no"):
            for index, port in enumerate(ports_value):
                if port[0] == ':':
                    ports_value[index] = port[1:]

            values['ports'] = ports_value
        else:
            values['expose'] = expose_value

    except (KeyError, TypeError):
        # No ports exposed/bound. Continue without them.
        ports = None

    # Iterate through values to finish building yaml dict.
    for key in values:
        value = values[key]
        if (value != None) and (value != "") and (value != []) and (value != 'null') and (value != {}) and (value != "default") and (value != 0) and (value != ",") and (value != "no"):
            ct[key] = value

    return cfile, networks


if __name__ == "__main__":
    main()

