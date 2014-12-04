#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import os

from probe_common import UNKNOWN, OK, WARNING, CRITICAL, Service

hostnames = {}
tcp = socket.SOCK_STREAM
udp = socket.SOCK_DGRAM

class NetworkService(Service):
    pass

def get_hostname_ip(hostname):
    # Caching system for IP
    if hostname in hostnames:
        return hostnames[hostname]
    remote_ip = socket.gethostbyname(hostname)
    hostnames[hostname] = remote_ip
    return remote_ip

class NetworkTcpService(NetworkService):
    port = 0
    
    def __init__(self, port=None):
        Service.__init__(self)
        if port is not None:
            self.port = port
    
    def __call__(self, hostname):
        remote_ip = get_hostname_ip(hostname)
        sock = socket.socket(socket.AF_INET, tcp)
        sock.settimeout(0.2)
        result = sock.connect_ex((remote_ip, self.port))
        if result == 0:
            return OK
        return CRITICAL

class NetworkUdpService(NetworkService):
    port = 0
    
    def __init__(self, port=None):
        Service.__init__(self)
        if port is not None:
            self.port = port
    
    def __call__(self, hostname):
        remote_ip = get_hostname_ip(hostname)
        sock = socket.socket(socket.AF_INET, udp)
        sock.settimeout(0.2)
        result = sock.connect_ex((remote_ip, self.port))
        try:
            sock.send('')
            sock.recv(10)
            is_open = False
        except socket.timeout:
            is_open = True
        except socket.error:
            is_open = False
        sock.close()
        if is_open:
            return OK
        return CRITICAL

class ping(NetworkService):
    def __call__(self, hostname):
        remote_ip = get_hostname_ip(hostname)
        response = os.system("ping -c 1 " + remote_ip + " > /dev/null")
        if response == 0:
            return OK
        return CRITICAL

class InternetCheck(ping):
    def __init__(self, hostnames):
        self.hostnames = hostnames
    
    def __call__(self):
        for hostname in self.hostnames:
            if ping.__call__(self, hostname) == OK:
                return OK
        return CRITICAL

class ftp(NetworkTcpService):
    port = 21

class ssh(NetworkTcpService):
    port = 22

class telnet(NetworkTcpService):
    port = 23

class smtp(NetworkTcpService):
    port = 25

class dns(NetworkTcpService):
    port = 53

class dhcp(NetworkUdpService):
    port = 67

class http(NetworkTcpService):
    port = 80

class pop3(NetworkTcpService):
    port = 110

class ntp(NetworkTcpService):
    port = 123

class imap(NetworkTcpService):
    port = 143

class imap(NetworkTcpService):
    port = 389

class https(NetworkTcpService):
    port = 443

class samba(NetworkTcpService):
    port = 445

class smtps(NetworkTcpService):
    port = 465

class imaps(NetworkTcpService):
    port = 993

class pop3s(NetworkTcpService):
    port = 995

class openvpn(NetworkUdpService):
    port = 1194

class mysql(NetworkTcpService):
    port = 3306

class sieve(NetworkTcpService):
    port = 4190

class sip(NetworkTcpService):
    port = 5060    

class postgresql(NetworkTcpService):
    port = 5432

class amavis(NetworkTcpService):
    port = 10024
