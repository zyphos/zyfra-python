#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage:
from zyfra import monitor

class MyMonitor(Monitor):
    def on_after_check_services(self):
        # Do what you want
        pass
    
    def on_changed_state(self, service_states, state_changed):
        # service_states = {'hostname':{'service_name': STATE,},} # STATE == monitor.UNKNOWN, monitor.OK, monitor.WARNING, monitor.CRITICAL
        # state_changed = {'hostname':['service_name',],}
        # Do what you want
        pass
    
    def on_new_critical_state(self, service_states, new_critical_states):
        # service_states = {'hostname':{'service_name': STATE,},} STATE == monitor.UNKNOWN, monitor.OK, monitor.WARNING, monitor.CRITICAL
        # new_critical_states = {'hostname':['service_name',],}
        # Do what you want
        pass

monitor = MyMonitor('myconfig.yaml')

YAML file: myconfig.yaml
- name: HostA
  hostname: 192.168.1.4
  services: ping,telnet

- name: HostB
  hostname: hostb.mydomain.net
  services: ping,http


To add user on linux system:
adduser --system --home / --no-create-home monitor --shell /bin/bash
"""

#from zyfra.tools import duration
import threading
from multiprocessing import Queue
from Queue import Empty as queue_empty
import time
import dateutil.relativedelta
import datetime
import signal

import os.path

import yaml

from probe_common import UNKNOWN, OK, WARNING, CRITICAL, State as cState
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
    
    def __repr__(self):
        return 'State [%s]->[%s]' % (self.old_value, self.value)

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

def probe_host(host, hostname, old_service_states, all_results, force_refresh, debug):
    all_results.set_host_probe_in_progress(hostname)
    all_results.convert_state2report()
    name = host['name']
    service_states = {}
    state_changed = []
    new_criticals = []
    bad_states = []
    ping = None
    if debug:
        print 'Probing %s (%s)' % (name, hostname)
    for service_obj in host['service_objs']:
        service_name = service_obj.name
        if debug:
            start_time = float(time.time())
            print service_name,
        if service_name in old_service_states:
            old_state = old_service_states[service_name]
        else:
            old_state = State()
        try:
            if isinstance(service_obj, network_services.NetworkService):
                state_value = service_obj(hostname)
                if service_obj.name == 'ping':
                    ping = state_value == OK
            elif isinstance(service_obj, host_service.HostService):
                if ping is None or ping:
                    force_refresh_service = service_obj.name in force_refresh
                    #state_value = service_obj.get_state(host['cmd_exec'], _no_cache_=force_refresh_service)
                    if service_obj.get_state.__name__ == '_delay_cache':
                        state_value = service_obj.get_state(host['cmd_exec'], _no_cache_=force_refresh_service)
                        state_value.is_cached = True
                    else:
                        state_value = service_obj.get_state(host['cmd_exec'])
                else:
                    state_value = cState(UNKNOWN)
            else:
                if debug:
                    print 'Unknown service type'
                # Unknown service type
                continue
        except Exception as e:
            state_value = cState(UNKNOWN)
            print 'Exception for host [%s(%s)] in module [%s]: %s' % (name, hostname, service_name, e)
            if debug:
                raise
        if debug:
            diff_time = float(time.time()) - start_time
            if diff_time < 0.001:
                print
            else:
                print '%.3f s' % (diff_time) 
        old_state_value = old_state.value
        if state_value != old_state_value:
            state_changed.append(service_name)
        if old_state_value != CRITICAL and state_value == CRITICAL:
            new_criticals.append(service_name)
        old_state(state_value)
        if state_value > 0:
            bad_states.append(service_name)
        service_states[service_name] = old_state
    all_results.unset_host_probe_in_progress(hostname)
    all_results.set_result(hostname, service_states, state_changed, new_criticals, bad_states)
    all_results.convert_state2report()

class ProbeAllResult():
    def __init__(self, old_service_states, hosts, queue2middle):
        self.old_service_states = old_service_states
        self.hosts = hosts
        self.queue2middle = queue2middle
        self.lock = threading.Lock()
        self.service_states = {}
        self.state_changed = {}
        self.new_criticals = {}
        self.bad_states = {}
        self.host_probe_in_progress = []

    def set_result(self, hostname, service_states, state_changed, new_criticals, bad_states):
        self.lock.acquire()
        try:
            if len(service_states):
                self.service_states[hostname] = service_states
            if len(state_changed):
                self.state_changed[hostname] = state_changed
            if len(new_criticals):
                self.new_criticals[hostname] = new_criticals
            if len(bad_states):
                self.bad_states[hostname] = bad_states
        finally:
            self.lock.release()
    
    def set_host_probe_in_progress(self, hostname):
        self.lock.acquire()
        try:
            if hostname not in self.host_probe_in_progress:
                self.host_probe_in_progress.append(hostname)
        finally:
            self.lock.release()
    
    def unset_host_probe_in_progress(self, hostname):
        self.lock.acquire()
        try:
            if hostname in self.host_probe_in_progress:
                self.host_probe_in_progress.remove(hostname) 
        finally:
            self.lock.release()
    
    def convert_state2report(self):
        self.lock.acquire()
        service_states = self.old_service_states.copy()
        service_states.update(self.service_states)
        report = []
        for host in self.hosts:
            hostdata = {}
            hostdata['name'] = host['name']
            hostname = host['hostname']
            hostdata['hostname'] = hostname
            if hostname not in service_states:
                continue
            hostdata['probing'] = hostname in self.host_probe_in_progress
            host_states = service_states[hostname]
            services = []
            state = OK
            for service_name in host['services']:
                if service_name not in host_states:
                    continue
                service_state = host_states[service_name]
                value = service_state.value
                service_state = value.state
                message = value.message
                if service_state > state:
                    state = service_state
                service_data = {}
                service_data['name'] = service_name
                service_data['state'] = render_status(service_state)
                service_data['message'] = message
                service_data['last_update'] = value.last_update
                service_data['last_update_ts'] = value.last_update_ts
                service_data['is_cached'] = value.is_cached
                services.append(service_data)
            hostdata['services'] = services
            hostdata['state'] = render_status(state)
            report.append(hostdata)
        self.lock.release()
        if self.queue2middle is not None:
            self.queue2middle.put(['set_status', report])
        return report

class Monitor(object):
    host_filename = 'hosts.yml'
    host_group_filename = 'groups.yml'
    default_remote_username = 'monitor'
    default_remote_password = None
    interval = 10 # in seconds
    debug = False
    webserver_port = None
    
    webserver_ssl = False
    webserver_certfile = None
    webserver_keyfile = None
    running = True
    thread_limit = None

    def __init__(self, host_filename=None, interval=None, internet_hosts=None):
        if host_filename is not None:
            self.host_filename = host_filename
        
        if interval is not None:
            self.interval = interval
        
        if internet_hosts is None:
            internet_hosts = ['www.yahoo.fr','www.yahoo.com']
        self.get_internet_state = network_services.InternetCheck(internet_hosts)
        self.hosts = self.read_hosts(self.host_filename)
        self.host_groups = self.read_host_groups(self.host_group_filename)
        self.host_by_hostname = dict([(host['hostname'],host) for host in self.hosts])
        self.internet_needed = False
        self.__instanciate_services()
        self.service_states = {}
        if self.webserver_port is not None:
            self.queue2probe = Queue()
            import web_server
            self.queue2middle = web_server.start_server(self.webserver_port, self.webserver_ssl, self.webserver_certfile, self.webserver_keyfile, self.queue2probe)
        else:
            self.queue2middle = None
        self.init()
    
    def stop(self, *args):
        self.running = False
        print 'Stop required'
    
    def init(self):
        # can be overcharged
        #signal.signal(signal.SIGINT, self.stop)
        try:
            first_check = True
            while True:
                force_refresh = {}
                # Threat queue
                try:
                    while True:
                        action, parameters = self.queue2probe.get(False)
                        if action == 'force_refresh':
                            hostname, service_name = parameters 
                            force_refresh.setdefault(hostname, []).append(service_name) 
                        pass
                except queue_empty:
                    pass
                    
                self.probe_hosts(first_check=first_check, thread_limit=self.thread_limit, force_refresh=force_refresh)
                first_check = False
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print 'CTRL-C pressed, quitting'
            if self.queue2middle is not None:
                self.queue2middle.put(['exit',''])
            
    def read_hosts(self, hostfilename):
        f = open(hostfilename)
        hosts = yaml.safe_load(f)
        f.close()
        return hosts
    
    def read_host_groups(self, filename):
        if filename is None or not os.path.isfile(filename):
            return {}
        f = open(filename)
        data = yaml.safe_load(f)
        f.close()
        host_groups = {}
        for i, group in enumerate(data):
            if 'name' not in group:
                print 'Name not found in group nr %s' % i
                continue
            name = group['name']
            host_groups[name] = group
        return host_groups
    
    def __instanciate_services(self):
        def get_service_instance(service, host):
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
            raise Exception('Service not found [%s] in host [%s]' % (service, host['name']))
        
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
            if 'services' in host:
                services = host['services']
                if isinstance(services, basestring):
                    services = services.split(',')
            else:
                services = []
            
            host['services'] = services
            groups = []
            if 'groups' in host:
                groups = host['groups']
                if isinstance(groups, basestring):
                    groups = groups.split(',')
            
            if groups:
                for group_name in groups:
                    if group_name not in self.host_groups:
                        raise Exception('Error group [%s] not found in host[%s]' % (group_name, host['name']))
                    group = self.host_groups[group_name]
                    if 'services' in group:
                        gs = group['services']
                        if isinstance(gs, basestring):
                            gs = gs.split(',')
                        host['services'] += gs
            
            if not services:
                raise Exception('Error services not defined in host[%s]' % host['name'])
            for service in services:
                host['service_objs'].append(get_service_instance(service, host))

    def temp_probe_first_result(self):
        temp_results = {}
        for host in self.hosts:
            if host.get('disabled'):
                continue
            service_results = {}
            for service_obj in host['service_objs']:
                s = State()
                s.value = cState(UNKNOWN, 'Probing...')
                service_results[service_obj.name] = s
            temp_results[host['hostname']] = service_results
        return temp_results

    def probe_hosts(self, first_check=False, thread_limit=None, force_refresh=None):
        if first_check:
            self.service_states = self.temp_probe_first_result()
        all_results = ProbeAllResult(self.service_states, self.hosts, self.queue2middle)
        all_results.convert_state2report()
        if self.internet_needed:
            internet_state = self.get_internet_state().state
            print 'Internet access is %s' % render_status(internet_state)
        else:
            internet_state = False
        print 'Checking services'
        active_threads = []
        for host in self.hosts:
            if host.get('disabled'):
                continue
            if host.get('internet_needed') and internet_state != OK:
                continue
            hostname = host['hostname']
            if hostname in self.service_states:
                old_service_state = self.service_states[hostname]
            else:
                old_service_state = {}
            force_refresh4hostname = force_refresh.get(hostname, [])
            if thread_limit == 0: # No thread at all
                probe_host(host, hostname, old_service_state, all_results, force_refresh4hostname,self.debug)
            else:
                while thread_limit is not None and len(active_threads) >= thread_limit:
                    for i, thread in enumerate(reversed(active_threads)):
                        if not thread.is_alive():
                             del active_threads[i]
                t = threading.Thread(target=probe_host, args=(host, hostname, old_service_state, all_results, force_refresh4hostname, self.debug))
                t.start()
                active_threads.append(t)
        
        for t in active_threads:
            t.join()
        print 'Done.'
        print
        self.service_states = all_results.service_states
        self.bad_states = all_results.bad_states
        if not first_check and len(all_results.state_changed):
            self.on_changed_state(all_results.service_states, all_results.state_changed)
        if not first_check and len(all_results.new_criticals):
            self.on_new_critical_state(all_results.service_states, all_results.new_criticals)
        all_results.convert_state2report()
        self.on_after_check_services()
        return all_results.state_changed
    
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
        # service_states = {'hostname':{'service_name': STATE,},} STATE == UNKNOWN, OK, WARNING, CRITICAL
        # state_changed = {'hostname':['service_name',],}
        pass
    
    def on_new_critical_state(self, service_states, new_critical_states):
        # service_states = {'hostname':{'service_name': STATE,},} STATE == UNKNOWN, OK, WARNING, CRITICAL
        # new_critical_states = {'hostname':['service_name',],}
        pass
