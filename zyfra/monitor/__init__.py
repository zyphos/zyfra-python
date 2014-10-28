#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage:
class MyMonitor(Monitor):
    def on_after_check_services(self):
        # Do what you want
        pass
    
    def on_changed_state(self, service_states, state_changed):
        # Do what you want
        pass
monitor = MyMonitor('myconfig.yaml')

YAML file:
- name: HostA
  hostname: 192.168.1.4
  services: ping,telnet

- name: HostB
  hostname: hostb.mydomain.net
  services: ping,http
"""

import yaml
import time
import dateutil.relativedelta
import datetime
dt1 = datetime.datetime.fromtimestamp(123456789) # 1973-11-29 22:33:09
dt2 = datetime.datetime.fromtimestamp(234567890) # 1977-06-07 23:44:50
rd = dateutil.relativedelta.relativedelta (dt2, dt1)

from probe_common import UNKNOWN, OK, WARNING, CRITICAL
import network_services

def time_delta2str(ts0, ts1):
    dts0 = datetime.datetime.fromtimestamp(ts0)
    dts1 = datetime.datetime.fromtimestamp(ts1)
    rd = dateutil.relativedelta.relativedelta (dts1, dts0)
    return "%dY %dM %dd %d:%d:%d" % (rd.years, rd.months, rd.days, rd.hours, rd.minutes, rd.seconds)

COLOR_GREEN = "\033[1;32m"
COLOR_RED = "\033[1;31m"
COLOR_LIGHT_GRAY = "\033[0;37m"
COLOR_CLEAR = "\033[0m"
COLOR_YELLOW = "\033[1;93m"
class State(object):
    value = UNKNOWN
    old_value = UNKNOWN
    timestamp = 0
    
    def __init(self):
        self.timestamp = time.time()

    def __call__(self, value):
        if value != self.value:
            self.old_value = self.value
            self.timestamp = time.time()
            self.value = value
    
    def get_since_txt(self):
        return time_delta2str(self.timestamp, time.time())

def render_status(status, console=False):
    color = COLOR_CLEAR
    txt = 'UNKNOWN'
    if status == OK:
        txt = 'OK'
        color = COLOR_GREEN
    if status == WARNING:
        txt = 'WARNING'
        color = COLOR_YELLOW
    elif status == CRITICAL:
        txt = 'CRITICAL'
        color = COLOR_RED
    if console:
        return '%s%s%s' % (color, txt, COLOR_CLEAR)
    else:
        return txt

class Monitor(object):
    def __init__(self, hostfilename, interval=10, internet_hosts=None):
        self.interval = interval
        if internet_hosts is None:
            internet_hosts = ['www.yahoo.fr','www.yahoo.com']
        self.get_internet_state = network_services.InternetCheck(internet_hosts)
        self.hosts = self.read_hosts(hostfilename)
        self.host_by_hostname = dict([(host['hostname'],host) for host in self.hosts])
        self.internet_needed = False
        self.__instanciate_services()
        self.service_states = {}
        self.init()
    
    def init(self):
        # need to be overcharged
        self.check_services(first_check=True)
        time.sleep(self.interval)
        while(True):
            self.check_services()
            time.sleep(self.interval)
            
    def read_hosts(self, hostfilename):
        f = open(hostfilename)
        hosts = yaml.safe_load(f)
        f.close()
        return hosts
    
    def __instanciate_services(self):
        def get_service_instance(service):
            if hasattr(network_services, service):
                return getattr(network_services, service)()
            else:
                raise Exception('Service not found: %s' % service)
        for host in self.hosts:
            host['service_objs'] = []
            if not host.get('disabled') and host.get('internet_needed'):
                self.internet_needed = True
            services = host['services']
            if isinstance(services, basestring):
                services = services.split(',')
            for service in services:
                host['service_objs'].append(get_service_instance(service))

    def check_services(self, first_check=False):
        service_states = {}
        state_changed = {}
        if self.internet_needed:
            internet_state = self.get_internet_state()
            print 'Internet access is %s' % render_status(internet_state)
        else:
            internet_state = False
        print 'Checking services',
        for host in self.hosts:
            if host.get('disabled'):
                continue
            if host.get('internet_needed') and internet_state != OK:
                continue

            name = host['name']
            hostname = host['hostname']
            #print '%s (%s)' % (name, hostname)
            for service_obj in host['service_objs']:
                service_name = service_obj.name
                if hostname in self.service_states and service_name in self.service_states[hostname]:
                    old_state = self.service_states[hostname][service_name]
                else:
                    old_state = State()
                state_value = service_obj(hostname)
                old_state_value = old_state.value
                if state_value != old_state_value:
                    state_changed.setdefault(hostname, []).append(service_name)
                old_state(state_value)
                service_states.setdefault(hostname, {})[service_name] = old_state
                #render_status(service_obj.name, state_value)
            print '.',
        print 'Done.'
        print
        self.service_states = service_states
        if not first_check and len(state_changed):
            self.on_changed_state(service_states, state_changed)
        self.on_after_check_services()
        return state_changed
    
    def report_state(self, service_states, console=False):
        txt = 'Service status:\n'
        for hostname in service_states:
            host = self.host_by_hostname[hostname]
            name = host['name']
            txt += '\n%s (%s)\n' % (name, hostname)
            for service_obj in host['service_objs']:
                service_name = service_obj.name
                state = service_states[hostname][service_name]
                txt += '%s: %s (since %s)\n' % (service_name,
                                                render_status(state.value, console),
                                                state.get_since_txt())
        return txt
    
    def report_changed(self, service_states, state_changed, console=False):
        txt = 'Service status changes:\n'
        for hostname in state_changed:
            host = self.host_by_hostname[hostname]
            name = host['name']
            txt += '\n%s (%s)\n' % (name, hostname)
            for service_name in state_changed[hostname]:
                state = service_states[hostname][service_name]
                txt += '%s: %s=>%s\n' % (service_name,
                                         render_status(state.old_value, console),
                                         render_status(state.value, console))
        return txt
    
    def on_after_check_services(self):
        pass
    
    def on_changed_state(self, service_states, state_changed):
        pass
