#!/usr/bin/env bash

set -ex

cp -rfp inventory/sample/* inventory/igz/
./gen_templates.py ${@}

ansible-playbook -i inventory/igz/hosts.ini cluster.yml -b \
    -e '{ kubectl_localhost: True }' -e '{ kubeconfig_localhost: True }'

ansible-playbook -i  inventory/igz/hosts.ini clients.yml
