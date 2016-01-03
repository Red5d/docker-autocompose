#! /usr/bin/env python

import pyaml, argparse, sys
from docker import Client

def main():
    parser = argparse.ArgumentParser(description='Generate docker-compose yaml definition from running container.')
    parser.add_argument('cname', type=str, help='The name of the container to process.')
    args = parser.parse_args()

    generate(args)
    

def generate(args):
    c = Client(base_url='unix://var/run/docker.sock')

    try:
        cid = [x['Id'] for x in c.containers() if args.cname in x['Names'][0]][0]
    except IndexError:
        print("That container is not running.")
        sys.exit(1)

    cinspect = c.inspect_container(cid)


    # Build yaml dict structure

    cfile = {}
    cfile[args.cname] = {}
    ct = cfile[args.cname]

    values = {
        'cap_add': cinspect['HostConfig']['CapAdd'],
        'cap_drop': cinspect['HostConfig']['CapDrop'],
        'cgroup_parent': cinspect['HostConfig']['CgroupParent'],
        'container_name': args.cname,
        'devices': cinspect['HostConfig']['Devices'],
        'dns': cinspect['HostConfig']['Dns'],
        'dns_search': cinspect['HostConfig']['DnsSearch'],
        'environment': cinspect['Config']['Env'],
        'extra_hosts': cinspect['HostConfig']['ExtraHosts'],
        'image': cinspect['Config']['Image'],
        'labels': cinspect['Config']['Labels'],
        'links': cinspect['HostConfig']['Links'],
        'log_driver': cinspect['HostConfig']['LogConfig']['Type'],
        'log_opt': cinspect['HostConfig']['LogConfig']['Config'],
        'net': cinspect['HostConfig']['NetworkMode'],
        'security_opt': cinspect['HostConfig']['SecurityOpt'],
        'ulimits': cinspect['HostConfig']['Ulimits'],
        'volumes': cinspect['HostConfig']['Binds'],
        'volume_driver': cinspect['HostConfig']['VolumeDriver'],
        'volumes_from': cinspect['HostConfig']['VolumesFrom'],
        'cpu_shares': cinspect['HostConfig']['CpuShares'],
        'cpuset': cinspect['HostConfig']['CpusetCpus']+','+cinspect['HostConfig']['CpusetMems'],
        'entrypoint': cinspect['Config']['Entrypoint'],
        'user': cinspect['Config']['User'],
        'working_dir': cinspect['Config']['WorkingDir'],
        'domainname': cinspect['Config']['Domainname'],
        'hostname': cinspect['Config']['Hostname'],
        'ipc': cinspect['HostConfig']['IpcMode'],
        'mac_address': cinspect['NetworkSettings']['MacAddress'],
        'mem_limit': cinspect['HostConfig']['Memory'],
        'memswap_limit': cinspect['HostConfig']['MemorySwap'],
        'privileged': cinspect['HostConfig']['Privileged'],
        'restart': cinspect['HostConfig']['RestartPolicy']['Name'],
        'read_only': cinspect['HostConfig']['ReadonlyRootfs'],
        'stdin_open': cinspect['Config']['OpenStdin'],
        'tty': cinspect['Config']['Tty']
    }

    # Check for command and add it if present.
    if cinspect['Config']['Cmd'] != None:
        values['command'] = " ".join(cinspect['Config']['Cmd']),

    # Check for exposed/bound ports and add them if needed.
    try:
        expose_value =  list(cinspect['Config']['ExposedPorts'].keys())
        ports_value = [cinspect['HostConfig']['PortBindings'][key][0]['HostIp']+':'+cinspect['HostConfig']['PortBindings'][key][0]['HostPort']+':'+key for key in cinspect['HostConfig']['PortBindings']]

        # If bound ports found, don't use the 'expose' value.
        if (ports_value != None) and (ports_value != "") and (ports_value != []) and (ports_value != 'null') and (ports_value != {}) and (ports_value != "default") and (ports_value != 0) and (ports_value != ",") and (ports_value != "no"):
            for index, port in enumerate(ports_value):
                if port[0] == ':':
                    ports_value[index] = port[1:]

            values['ports'] = ports_value
        else:
            values['expose'] = expose_value

    except KeyError:
        # No ports exposed/bound. Continue without them.
        ports = None

    # Iterate through values to finish building yaml dict.
    for key in values:
        value = values[key]
        if (value != None) and (value != "") and (value != []) and (value != 'null') and (value != {}) and (value != "default") and (value != 0) and (value != ",") and (value != "no"):
            ct[key] = value

    # Render yaml file
    pyaml.p(cfile)

if __name__ == "__main__":
    main()

