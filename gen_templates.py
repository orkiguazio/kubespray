#!/usr/bin/env python
import sys
import json
import socket
import logging
import argparse
import subprocess

import jinja2
import paramiko


def get_interafce_ip_addr(hostname, username, password, interface):
    """
        SSH to a host and get its IP
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Connect to remote host
        ssh.connect(hostname=hostname, username=username, password=password, timeout=15)
        cmd = "/usr/sbin/ip -4 -o addr show dev {}|awk '{{print $4}}'|cut -d '/' -f1".format(interface)
        _, stdout, _ = ssh.exec_command(cmd)
        mlnx_ip = stdout.read().strip()

        # Validate it's an IP
        socket.inet_aton(mlnx_ip)

        # Close SSH connection
        ssh.close()
    except Exception:
        raise Exception('Failed to connect/get bond0 IP from {}'.format(hostname))
    return mlnx_ip


class ClientNode(object):

    def __init__(self, mgmt_ip, user, password):
        self.mgmt_ip = mgmt_ip
        self.user = user
        self.password = password

    @classmethod
    def from_naipi(cls, config):
        return cls(config['address'], config['username'], config['password'])


class ServerHost(object):

    def __init__(self, mgmt_ip, user, password, data_interface, has_etcd, is_master):
        if data_interface is None:
            data_interface = 'bond0'

        self.mgmt_ip = mgmt_ip
        self.user = user
        self.password = password
        self.data_ip = get_interafce_ip_addr(mgmt_ip, user, password, data_interface)
        self.has_etcd = has_etcd
        self.is_master = is_master

    @classmethod
    def from_naipi(cls, config):
        roles = config['roles']
        if 'kube-node' not in roles:
            return None

        mgmt_ip = config['address']
        user = config['username']
        password = config['password']
        data_interface = config.get('dataplane-interface')

        return cls(mgmt_ip, user, password, data_interface,
                   has_etcd='kube-etcd' in roles, is_master='kube-master' in roles)


def _gen_templates(path, **kwargs):
    with open(path + '.jinja2') as fh:
        data = fh.read()

    template = jinja2.Template(
        data, keep_trailing_newline=True, trim_blocks=True,
        undefined=jinja2.StrictUndefined)
    generated_data = template.render(**kwargs)

    with open(path, 'w') as fh:
        fh.write(generated_data)


def get_servers(ips, user, password):
    masters_count = 3 if len(ips) >= 3 else 1
    for i, server in enumerate(ips):
        server_args = server.split(',')
        try:
            mgmt_ip, data_interface = server_args
        except ValueError:
            mgmt_ip, = server_args
            data_interface = None

        is_master = i < masters_count
        yield ServerHost(mgmt_ip, user, password, data_interface, has_etcd=is_master, is_master=is_master)


def from_naipi(data):
    config = json.loads(data)['setup']
    servers = (ServerHost.from_naipi(c) for c in config['clients'])
    servers = [s for s in servers if s is not None]
    clients = [ClientNode.from_naipi(c) for c in config['nodes']]
    return servers, clients


def _parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', dest='servers', action='append', default=[])
    parser.add_argument('-c', '--client', dest='clients', action='append', default=[])
    parser.add_argument('-u', '--user', default='iguazio')
    parser.add_argument('-p', '--password', default='24tango')
    parser.add_argument('-n', '--naipi-config')
    return parser.parse_args()


def main():
    log_fmt = '%(asctime)s %(levelname)s: %(filename)s:%(lineno)d: %(message)s'
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_fmt)

    args = _parse()

    if args.naipi_config is not None:
        servers, clients = from_naipi(args.naipi_config)
    else:
        servers = list(get_servers(args.servers, args.user, args.password))
        clients = [ClientNode(ip, args.user, args.password) for ip in args.clients]

    cmd = ['python3', 'contrib/inventory_builder/inventory.py']
    cmd.extend(s.mgmt_ip for s in servers)
    subprocess.check_output(cmd, env={'CONFIG_FILE': 'inventory/igz/hosts.ini'})

    logging.info('generating template files')
    _gen_templates(path='inventory/igz/hosts.ini', servers=servers, clients=clients)


if __name__ == '__main__':
    main()
