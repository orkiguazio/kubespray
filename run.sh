#!/usr/bin/env bash

set -ex

cp -rfp inventory/sample/* inventory/igz/
./gen_templates.py ${@}

ansible-playbook -i inventory/igz/hosts.ini offline_cache.yml \
    -e 'release_cache_dir=./releases' -e '{ skip_downloads: True }'

ansible-playbook -i inventory/igz/hosts.ini cluster.yml -b \
    -e '{ kubectl_localhost: True }' -e '{ kubeconfig_localhost: True }' \
    -e '{ deploy_container_engine: False }' -e '{ skip_downloads: True }' \
    -e kube_proxy_mode=iptables

ansible-playbook -i  inventory/igz/hosts.ini clients.yml
