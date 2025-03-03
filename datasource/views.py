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
# 1. Allow unauthorized access in webvirtcloud/settings.py:
#
# LOGIN_REQUIRED_IGNORE_PATHS = [
#     r"^/datasource/nocloud/meta-data$",
#     r"^/datasource/nocloud/user-data$",
# ]
#
# 2. Optionally, restrict access to VM IPs with HTTPS only in conf\nginx\webvirtcloud.conf:
#
# server {
#     location ~* ^/datasource/ {
#         allow 192.168.122.0/24;  # Allow only VMs in this subnet
#         deny all;  # Block all other IPs
# 
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header Host $host;
#         proxy_set_header X-Forwarded-Proto https;
#         proxy_connect_timeout 1800;
#         proxy_read_timeout 1800;
#         proxy_send_timeout 1800;
#         client_max_body_size 1024M;
#     }
#     ...
# }
# ...
#

def os_metadata_json(request):
    """
    :param request:
    :return:
    """
    ip = get_client_ip(request)
    hostname = get_hostname_by_ip(ip)
    response = response = f"instance-id: {OS_UUID}\nhostname: {hostname}"
    return HttpResponse(response, content_type="text/plain")


def os_userdata(request):
    """
    :param request:
    :return:
    """
    ip = get_client_ip(request)
    hostname = get_hostname_by_ip(ip)
    vname = hostname.split(".")[0]

    instance_keys = []
    userinstances = UserInstance.objects.filter(instance__name=vname)

    for ui in userinstances:
        keys = UserSSHKey.objects.filter(user=ui.user)
        for k in keys:
            instance_keys.append(k.keypublic)

    # Create the user data
    user_data = "#cloud-config\n"
    user_data += f"hostname: {vname}\n"
    user_data += "manage_etc_hosts: true\n"
    
    if instance_keys:
        user_data += "ssh_authorized_keys:"
        for key in instance_keys:
            user_data += f"\n  - {key}"

    # Return as plain text
    return HttpResponse(user_data, content_type="text/plain")


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


def get_hostname_by_ip(ip):
    """
    :param ip:
    :return:
    """
    try:
        # Try DNS first
        addrs = socket.gethostbyaddr(ip)
        return addrs[0]
    except socket.herror:
        pass  # No reverse DNS found

    # Search all VM instances for assigned IP
    for instance in Instance.objects.all():
        net_devices = instance.proxy.get_net_devices()
        for net in net_devices:
            ipv4_list = net.get("ipv4") or []
            ipv6_list = net.get("ipv6") or []

            if ip in ipv4_list or ip in ipv6_list:
                return instance.name  # Return the VM name

    return ip  # Default to returning the raw IP


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

        fqdn = get_hostname_by_ip(compute.hostname)
        url = f"{conn.get_console_type()}://{fqdn}:{conn.get_console_port()}"
        response = url
        return HttpResponse(response)
    except libvirtError:
        err = "Error getting VDI URL for %(name)s" % {"name": vname}
        raise Http404(err)
