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
import time
import dateutil.relativedelta
import datetime
import signal



import yaml

dt1 = datetime.datetime.fromtimestamp(123456789) # 1973-11-29 22:33:09
dt2 = datetime.datetime.fromtimestamp(234567890) # 1977-06-07 23:44:50
rd = dateutil.relativedelta.relativedelta (dt2, dt1)

from probe_common import UNKNOWN, OK, WARNING, CRITICAL
import network_services
import host_service

def time_delta2str(ts0, ts1):
    dts0 = datetime.datetime.fromtimestamp(ts0)
    dts1 = datetime.datetime.fromtimestamp(ts1)
    rd = dateutil.relativedelta.relativedelta (dts1, dts0)
    return "%dY %dM %dd %d:%d:%d" % (rd.years, rd.months, rd.days, rd.hours, rd.minutes, rd.seconds)

console_color = {'red': "\033[1;31m",
                 'green': "\033[1;32m",
                 'light_gray': "\033[0;37m",
                 'clear': "\033[0m",
                 'yellow': "\033[1;93m",
                 }
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

def render_status(status, target='txt'):
    color = 'clear'
    txt = 'UNKNOWN'
    if status == OK:
        txt = 'OK'
        color = 'green'
    if status == WARNING:
        txt = 'WARNING'
        color = 'yellow'
    elif status == CRITICAL:
        txt = 'CRITICAL'
        color = 'red'
    if target == 'console':
        return '%s%s%s' % (console_color[color], txt, console_color['clear'])
    elif target == 'html':
        return "<span style='color:%s;font-weight:bold;'>%s</span>" % txt
    else:
        return txt

class Monitor(object):
    default_remote_username = 'monitor'
    default_remote_password = None
    debug = False
    webserver_port = None
    running = True

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
        if self.webserver_port is not None:
            import web_server
            self.queue2middle = web_server.start_server(self.webserver_port)
        self.init()
    
    def stop(self, *args):
        self.running = False
        print 'Stop required'
    
    def init(self):
        # need to be overcharged
        #signal.signal(signal.SIGINT, self.stop)
        try:
            self.check_services(first_check=True)
            time.sleep(self.interval)
            while(True):
                self.check_services()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print 'CTRL-C pressed, quitting'
            self.queue2middle.put(['exit',''])
            
    def read_hosts(self, hostfilename):
        f = open(hostfilename)
        hosts = yaml.safe_load(f)
        f.close()
        return hosts
    
    def __instanciate_services(self):
        def get_service_instance(service):
            split = service.split(':', 1)
            if len(split) == 1:
                service_name = service
                params = []
            else:
                service_name, params = split
                params = params.split(',')
            if hasattr(network_services, service):
                return getattr(network_services, service)(*params)
            if hasattr(host_service, service):
                return getattr(host_service, service)(*params)
            raise Exception('Service not found: %s' % service)
        for host in self.hosts:
            if host['hostname'] == 'localhost':
                host['cmd_exec'] = host_service.CmdLocalhost()
            else:
                username = host.get('username', self.default_remote_username)
                target = '%s@%s' % (username, host['hostname'])
                password = host.get('password', self.default_remote_password)
                host['cmd_exec'] =  host_service.CmdSsh(target, password)
            host['service_objs'] = []
            if not host.get('disabled') and host.get('internet_needed'):
                self.internet_needed = True
            services = host['services']
            if isinstance(services, basestring):
                services = services.split(',')
            host['services'] = services
            for service in services:
                host['service_objs'].append(get_service_instance(service))

    def check_services(self, first_check=False):
        service_states = {}
        state_changed = {}
        bad_states = {}
        if self.internet_needed:
            internet_state = self.get_internet_state()
            print 'Internet access is %s' % render_status(internet_state)
        else:
            internet_state = False
        print 'Checking services'
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
                try:
                    if isinstance(service_obj, network_services.NetworkService):
                        state_value = service_obj(hostname)
                    elif isinstance(service_obj, host_service.HostService):
                        state_value = service_obj.get_state(host['cmd_exec'])
                    else:
                        # Unknown service type
                        continue
                except Exception as e:
                    state_value = UNKNOWN
                    print 'Exception for host [%s(%s)] in module [%s]: %s' % (name, hostname, service_name, e)
                    if self.debug:
                        raise
                old_state_value = old_state.value
                if state_value != old_state_value:
                    state_changed.setdefault(hostname, []).append(service_name)
                old_state(state_value)
                if state_value > 0:
                    bad_states.setdefault(hostname, []).append(service_name)
                service_states.setdefault(hostname, {})[service_name] = old_state
                #render_status(service_obj.name, state_value)
            print '.'
        print 'Done.'
        print
        self.service_states = service_states
        self.bad_states = bad_states
        if not first_check and len(state_changed):
            self.on_changed_state(service_states, state_changed)
        if self.webserver_port is not None:
            self.queue2middle.put(['set_status', self.convert_state2report(service_states)]) #
        self.on_after_check_services()
        return state_changed
    
    def convert_state2report(self, service_states):
        report = []
        for host in self.hosts:
            hostdata = {}
            hostdata['name'] = host['name']
            hostname = host['hostname']
            hostdata['hostname'] = hostname
            if hostname not in service_states:
                continue
            host_states = service_states[hostname]
            services = []
            state = OK
            for service_name in host['services']:
                if service_name not in host_states:
                    continue
                service_state = host_states[service_name].value
                if service_state > state:
                    state = service_state
                service_data = {}
                service_data['name'] = service_name
                service_data['state'] = render_status(service_state)
                services.append(service_data)
            hostdata['services'] = services
            hostdata['state'] = render_status(state)
            report.append(hostdata)
        return report
    
    def report_state(self, service_states, target='txt'):
        if len(service_states) == 0:
            return ''
        txt = 'Service status:\n'
        for host in self.hosts:
            hostname = host['hostname']
            if hostname not in service_states:
                continue
            name = host['name']
            txt += '\n%s (%s)\n' % (name, hostname)
            hostname_service_states = service_states[hostname]
            def render(service_name, state):
                return '%s: %s (since %s)\n' % (service_name,
                                                render_status(state.value, target),
                                                state.get_since_txt())
            if isinstance(hostname_service_states, dict):
                for service_obj in host['service_objs']:
                    service_name = service_obj.name
                    state = hostname_service_states[service_name]
                    txt += render(service_name, state)
            else:
                for service_name in hostname_service_states:
                    state = self.service_states[hostname][service_name]
                    txt += render(service_name, state)
        return txt
    
    def report_changed(self, service_states, state_changed, target='txt'):
        cr = '\n'
        if target == 'sms':
            cr = ' '
        txt = 'Service status changes:' + cr
        for host in self.hosts:
            hostname = host['hostname']
            if hostname not in state_changed:
                continue
            name = host['name']
            txt += cr + '%s (%s)' % (name, hostname) + cr
            for service_name in state_changed[hostname]:
                state = service_states[hostname][service_name]
                txt += '%s: %s=>%s' % (service_name,
                                         render_status(state.old_value, target),
                                         render_status(state.value, target)) + cr
        return txt
    
    def on_after_check_services(self):
        pass
    
    def on_changed_state(self, service_states, state_changed):
        pass
