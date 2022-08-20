#! /usr/bin/env python3
import datetime
import sys, argparse, pyaml, docker
from collections import OrderedDict


def list_container_names():
    c = docker.from_env()
    return [container.name for container in c.containers.list(all=True)]


def main():
    parser = argparse.ArgumentParser(description='Generate docker-compose yaml definition from running container.')
    parser.add_argument('-a', '--all', action='store_true', help='Include all active containers')
    parser.add_argument('-v', '--version', type=int, default=3, help='Compose file version (1 or 3)')
    parser.add_argument('cnames', nargs='*', type=str, help='The name of the container to process.')
    parser.add_argument('-c', '--createvolumes', action='store_true', help='Create new volumes instead of reusing existing ones')
    args = parser.parse_args()

    container_names = args.cnames
    if args.all:
        container_names.extend(list_container_names())

    struct = {}
    networks = {}
    volumes = {}
    containers = {}
    for cname in container_names:
        cfile, c_networks, c_volumes = generate(cname, createvolumes=args.createvolumes)

        struct.update(cfile)

        if not c_networks == None:
            networks.update(c_networks)
        if not c_volumes == None:
            volumes.update(c_volumes)
    
    # moving the networks = None statemens outside of the for loop. Otherwise any container could reset it.
    if len(networks) == 0:
    	networks = None
    if len(volumes) == 0:
    	volumes = None
    render(struct, args, networks, volumes)

def render(struct, args, networks, volumes):
    # Render yaml file
    if args.version == 1:
        pyaml.p(OrderedDict(struct))
    else:
        ans = {'version': '"3.6"', 'services': struct}

        if networks is not None:
            ans['networks'] = networks

        if volumes is not None:
            ans['volumes'] = volumes

        pyaml.p(OrderedDict(ans))


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


def generate(cname, createvolumes=False):
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

    default_networks = ['bridge', 'host', 'none']

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
        'networks': {x for x in cattrs['NetworkSettings']['Networks'].keys() if x not in default_networks},
        'security_opt': cattrs['HostConfig']['SecurityOpt'],
        'ulimits': cattrs['HostConfig']['Ulimits'],
# the line below would not handle type bind
#        'volumes': [f'{m["Name"]}:{m["Destination"]}' for m in cattrs['Mounts'] if m['Type'] == 'volume'],
        'mounts': cattrs['Mounts'], #this could be moved outside of the dict. will only use it for generate
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
        assumed_default_network = list(cattrs['NetworkSettings']['Networks'].keys())[0]
        values['network_mode'] = assumed_default_network
        networks = None
    else:
        networklist = c.networks.list()
        for network in networklist:
            if network.attrs['Name'] in values['networks']:
                networks[network.attrs['Name']] = {'external': (not network.attrs['Internal']),
                                                   'name': network.attrs['Name']}
#     volumes = {}
#     if values['volumes'] is not None:
#         for volume in values['volumes']:
#             volume_name = volume.split(':')[0]
#             volumes[volume_name] = {'external': True}
#     else:
#         volumes = None
        
    # handles both the returned values['volumes'] (in c_file) and volumes for both, the bind and volume types
    # also includes the read only option
    volumes = {}
    mountpoints = []
    if values['mounts'] is not None:
        for mount in values['mounts']:
            destination = mount['Destination']
            if not mount['RW']:
                destination = destination + ':ro'
            if mount['Type'] == 'volume':
                mountpoints.append(mount['Name'] + ':' + destination)
                if not createvolumes:
                    volumes[mount['Name']] = {'external': True}    #to reuse an existing volume ... better to make that a choice? (cli argument)
            elif mount['Type'] == 'bind':
                mountpoints.append(mount['Source'] + ':' + destination)
        values['volumes'] = mountpoints
    if len(volumes) == 0:
        volumes = None
    values['mounts'] = None #remove this temporary data from the returned data


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

    return cfile, networks, volumes


if __name__ == "__main__":
    main()
