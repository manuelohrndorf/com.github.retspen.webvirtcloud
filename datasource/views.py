import json
import re
import socket

from accounts.models import UserInstance, UserSSHKey
from computes.models import Compute
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from instances.models import Instance
from libvirt import libvirtError
from vrtManager.instance import wvmInstance

OS_UUID = "iid-dswebvirtcloud"

# To enable NoCloud datasource:
#
# 1. Allow unauthorized access in webvirtcloud/settings.py: ENABLE_DATASOURCE = True
#
# 2. Optionally, restrict access to VM IPs with HTTPS only in conf\nginx\webvirtcloud.conf:
#
# server {
#     listen 443 ssl;
#     ...
#     location /datasource/ {
#         allow 192.168.122.0/24;  # Allow only VMs in this subnet
#         deny all;  # Block all other IPs
# 
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto https;
#         proxy_set_header Host $host;
#         proxy_connect_timeout 1800;
#         proxy_read_timeout 1800;
#         proxy_send_timeout 1800;
#         client_max_body_size 1024M;
#     }
#     ...
# }
# ...
# server {
#     listen 80;
#     ...
#     location /datasource/ {
#         allow 192.168.122.0/24;  # Allow only VMs in this subnet
#         allow 130.92.64.118;  # hydra.inf.unibe.ch
#         deny all;  # Block all other IPs
# 
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header Host $host;
#         proxy_connect_timeout 1800;
#         proxy_read_timeout 1800;
#         proxy_send_timeout 1800;
#         client_max_body_size 1024M;
#     }
# }

def os_metadata_json(request):
    """
    :param request:
    :return:
    """
    response = f"instance-id: {OS_UUID}"
    return HttpResponse(response, content_type="text/plain")


def os_userdata(request):
    """
    :param request:
    :return:
    """
    ip = get_client_ip(request)
    vname = get_vmname_by_ip(ip)

    instance_keys = []
    userinstances = UserInstance.objects.filter(instance__name=vname)

    for ui in userinstances:
        keys = UserSSHKey.objects.filter(user=ui.user)
        for k in keys:
            instance_keys.append(k.keypublic)

    # Create the user data
    user_data = "#cloud-config\n"
    user_data += f"hostname: {get_hostname(vname)}\n"
    #user_data += "manage_etc_hosts: true\n"
    
    if instance_keys:
        user_data += "ssh_authorized_keys:"
        for key in instance_keys:
            user_data += f"\n  - {key}"

    # Return as plain text
    return HttpResponse(user_data, content_type="text/plain")


def os_metadata_for_mac(request, mac):
    """
    Retrieve meta-data for a specific VM based on its MAC address.
    """
    mac = mac.lower().replace("-", ":")  # Normalize MAC format

    # Find the instance with the matching MAC address
    instance = None
    for inst in Instance.objects.all():
        net_devices = inst.proxy.get_net_devices()
        for net in net_devices:
            if net.get("mac") == mac:
                instance = inst
                break
        if instance:
            break

    if not instance:
        raise Http404("No VM found: " + mac)

    # Retrieve associated SSH keys
    instance_keys = []
    userinstances = UserInstance.objects.filter(instance=instance)
    for ui in userinstances:
        keys = UserSSHKey.objects.filter(user=ui.user)
        for key in keys:
            instance_keys.append(key.keypublic)

    # Construct meta-data response
    metadata = {
        "meta-data": {
            "instance-id": f"vm-{instance.id}",
            "local-hostname": get_hostname(instance.name),
            "public-keys": instance_keys,
        }
    }

    return HttpResponse(json.dumps(metadata), content_type="application/json")


def get_hostname(vm_name: str) -> str:
    """
    Converts a VM name into a valid hostname for /etc/hosts and /etc/hostname.

    - Removes invalid characters (only allows a-z, 0-9, and '-')
    - Ensures it starts and ends with a letter or number
    - Limits length to 63 characters
    - Converts to lowercase
    """

    # Convert to lowercase
    hostname = vm_name.lower()

    # Replace invalid characters with a hyphen (only allow a-z, 0-9, and '-')
    hostname = re.sub(r'[^a-z0-9-]', '-', hostname)

    # Remove leading or trailing hyphens
    hostname = hostname.strip('-')

    # Ensure it does not start with a number
    if hostname and hostname[0].isdigit():
        hostname = "vm-" + hostname

    # Truncate to 63 characters (max allowed for a hostname)
    hostname = hostname[:63]

    # Ensure the hostname is not empty (fallback if everything was removed)
    return hostname if hostname else "vm-default"


def get_client_ip(request):
    """
    :param request:
    :return:
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()  # Get the first (original) IP
    else:
        ip = request.META.get("REMOTE_ADDR")  # 127.0.0.1 if reverse proxy by NGINX
    return ip


def get_vmname_by_ip(ip):
    """
    :param ip: The IP address to resolve
    :return: The VM name if found, otherwise the IP
    """
    from django.conf import settings

    # Get MAC address from IP mapping
    mac = settings.IP_TO_MAC.get(ip)

    if not mac:
        return ip  # No MAC found for IP, return IP

    # Search all VM instances for matching MAC address
    for instance in Instance.objects.all():
        net_devices = instance.proxy.get_net_devices()
        for net in net_devices:
            if net.get("mac") == mac:
                return instance.name  # Return the VM name

    return ip  # Default to returning the raw IP if not found


def get_vdi_url(request, compute_id, vname):
    """
    :param request:
    :param vname:
    :return:
    """
    compute = get_object_or_404(Compute, pk=compute_id)

    try:
        conn = wvmInstance(
            compute.hostname, compute.login, compute.password, compute.type, vname
        )

        fqdn = get_hostname(get_vmname_by_ip(compute.hostname))
        url = f"{conn.get_console_type()}://{fqdn}:{conn.get_console_port()}"
        response = url
        return HttpResponse(response)
    except libvirtError:
        err = "Error getting VDI URL for %(name)s" % {"name": vname}
        raise Http404(err)
