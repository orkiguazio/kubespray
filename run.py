#!/usr/bin/env python

import sys
import json
import socket
import os.path
import logging
import argparse
import subprocess


import gen_templates


def _run_ansible(playbooks_dir, playbook, become=False, skip_tags=(), tags=(), **kwargs):
    playbook = '{}.yml'.format(playbook)
    extra_vars = json.dumps(kwargs)
    cmd = ['ansible-playbook', '-i', 'inventory/igz/hosts.ini', playbook, '--extra-vars', extra_vars]
    if skip_tags:
        cmd.append('--skip-tag={}'.format(','.join(skip_tags)))

    if tags:
        cmd.append('--tags={}'.format(','.join(tags)))

    if become:
        cmd.append('--become')

    subprocess.check_call(cmd, cwd=playbooks_dir, stdout=sys.stdout, stderr=sys.stderr)


def run(do_reset):
    playbooks_dir = os.path.dirname(__file__)
    if do_reset:
        _run_ansible(playbooks_dir, 'reset_igz', become=True, kube_proxy_mode='iptables')

    _run_ansible(playbooks_dir, 'offline_cache', release_cache_dir='./releases', skip_downloads=True)
    _run_ansible(playbooks_dir, 'cluster', become=True, kubectl_localhost=True,
                 kubeconfig_localhost=True, deploy_container_engine=False, skip_downloads=True,
                 preinstall_selinux_state='disabled', kube_proxy_mode='iptables')
    _run_ansible(playbooks_dir, 'clients')


def _k8s_node_ips(args):
    mgmt, data = args.split(',')
    socket.inet_aton(mgmt)
    socket.inet_aton(data)
    return mgmt, data


def _validate_ip(ip):
    socket.inet_aton(ip)
    return ip


def cli_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', dest='servers', action='append', default=[])
    parser.add_argument('-c', '--client', dest='clients', action='append', default=[])
    parser.add_argument('-u', '--user', default='iguazio')
    parser.add_argument('-p', '--password', default='24tango')
    parser.add_argument('-n', '--naipi-config')
    parser.add_argument('-r', '--reset', action='store_true',
                        help='do reset before deploy, delete restart docker, dont run from within k8s cluster')
    return parser.parse_args()


def main():
    log_fmt = '%(asctime)s %(levelname)s: %(filename)s:%(lineno)d: %(message)s'
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_fmt)

    args = cli_parser()
    if args.naipi_config:
        gen_templates.from_naipi(args.naipi_config)
    else:
        gen_templates.from_cli(args.servers, args.clients, args.user, args.password)

    run(args.reset)


if __name__ == '__main__':
    main()
