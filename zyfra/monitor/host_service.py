# -*- coding: utf-8 -*-

import datetime
import subprocess

from .. import ssh_session, tools
from .probe_common import UNKNOWN, OK, WARNING, CRITICAL, Service, ProbeException, StateValue

"""TODO:
"""

class Cmd(object):
    def file_exists(self, filename):
        #result = self('if [ -f %s ]; then echo 1;else echo 0; fi' % filename, shell=True)
        result = self(['[ -f %s ] && echo -n 1 || echo -n 0' % filename], shell=True)
        return result == '1'

class CmdSsh(Cmd):
    def __init__(self, target, password=None):
        self.target = target
        self.password = password
    
    def __call__(self, cmd, raise_empty=True, shell=False, debug=False):
        lnk = ssh_session.get_ssh_link(self.target, password=self.password)
        result = lnk.cmd(' '.join(cmd))
        if debug:
            print()
            print(' '.join(cmd))
            print(repr(result))
            print()
        result = result.decode()
        if raise_empty and result == '':
            raise ProbeException('Empty result for CmdSsh: %s' % cmd)
        return result

class CmdLocalhost(Cmd):
    def __call__(self, cmd, raise_empty=True, shell=False, debug=False):
        if shell:
            cmd = ' '.join(cmd)
        result = subprocess.check_output(cmd, shell=shell, stderr=subprocess.STDOUT)
        if debug:
            print()
            print(cmd)
            print(repr(result))
            print()
        result = result.decode()
        if raise_empty and result == '':
            raise ProbeException('Empty result for CmdLocalhost: %s' % cmd)
        return result
        
class HostService(Service):
    cmd = ['ls']
    shell = False
    
    def _parse_result(self, result):
        return result
    
    def get_state(self, cmd_exec):
        result = cmd_exec(self.cmd, shell=self.shell)
        return self._parse_result(result)

    def ssh(self, target, password=None):
        cmd_exec = CmdSsh(target, password)
        return self.get_state(cmd_exec)
    
    def localhost(self):
        cmd_exec = CmdLocalhost()
        return self.get_state(cmd_exec)

class mount_usage(HostService):
    def _get_mount_usages(self, cmd_exec):
        mounts = {}
        
        # Check space
        result = cmd_exec(['df','-P']) 
        for row in result.split('\n')[1:-1]:
            device, size, used_space, free_space, pc, mount_point = row.split(None, 5)
            size = int(size)
            used_space = int(used_space)
            free_space = int(free_space)
            if device in ('none', 'cgroup','udev','tmpfs','cgmfs','varrun','varlock','devshm','lrm'):
                continue
            if mount_point[:6] == '/snap/':
                continue

            mounts[mount_point] = {'device': device,
                                   'size': size,
                                   'used_space': used_space,
                                   'free_space': free_space,
                                   'pc_space': pc}
        
        # Check inodes
        result = cmd_exec(['df','-i'])
        for row in result.split('\n')[1:-1]:
            device, total_inode, used_inode, free_inode, pc, mount_point = row.split(None, 5)
            total_inode = int(total_inode)
            used_inode = int(used_inode)
            free_inode = int(free_inode)
            if mount_point not in mounts:
                continue
            data = {'total_inode': total_inode,
                    'used_inode': used_inode,
                    'free_inode': free_inode,
                    'pc_inode': pc
                    }
            mounts[mount_point].update(data)
        return mounts
    
    def _str_data(self, data):
        mountpoints = list(data.keys())
        mountpoints.sort()
        return '\n'.join(['space|inode'] + ['% 4s % 4s %s' % (data[mp]['pc_space'],data[mp]['pc_inode'], mp) for mp in mountpoints])
    
    @tools.delay_cache(60) # 1 min cached
    def get_state(self, cmd_exec):
        state = OK
        mount_usages = self._get_mount_usages(cmd_exec)
        for mount_name, mount_usage in mount_usages.items():
            free_ratio = mount_usage['free_space'] / float(mount_usage['size'])
            if free_ratio <= 0.1:
                state = CRITICAL
            elif free_ratio <= 0.2:
                state = WARNING 
        return StateValue(state, self._str_data(mount_usages))

class loadavg(HostService):
    def _get_loads(self, cmd_exec):
        'return: [loadavg_1m, loadavg_5m, loadavg_15m]'
        cmd = ['cat', '/proc/loadavg']
        result = cmd_exec(cmd)
        return [float(x) for x in result.split()[:3]]
    
    @tools.delay_cache(60) # 1 min cached
    def get_state(self, cmd_exec):
        loads = self._get_loads(cmd_exec)
        state_5m = loads[1]
        state = WARNING
        if state_5m < 1:
            state = OK
        return StateValue(state, ' - '.join(['%.2f' % l for l in loads]))

class process(HostService):
    process_name = None
    shell = True

    def __init__(self, name = None, cmd = None):
        if cmd is None:
            cmd = self.process_name
        if cmd is None:
            raise ProbeException('No process cmd defined')
        #self.cmd = ['ps', 'aux', '|', 'grep "%s"' % cmd]
        self.cmd = ['ps', 'aux', '|', 'grep', '"%s"' % cmd]
        HostService.__init__(self)
        if name is not None:
            self.name = name

    def _parse_result(self, result):
        if len(result.split('\n')) > 3:
            return StateValue(OK)
        return StateValue(CRITICAL)

class raid(HostService):
    def _get_raid_status(self, cmd_exec):
        cmd = ['cat', '/proc/mdstat']
        result = cmd_exec(cmd)
        raids = {}
        rows = result.split('\n')[1:-2]
        i = 0
        while i < len(rows):
            row = rows[i]
            if row.find(' : ') == -1:
                i += 1
                continue
            name, composition = row.split(' : ')
            i += 1
            rsplit = rows[i].split()
            size = rsplit[0]
            disk_ratio = rsplit[-2]
            status = rsplit[-1]
            i += 1
            if i < len(rows) and rows[i].strip() != '' and rows[i].find('resync') != -1:
                msg = rows[i].strip()
                i += 1
            else:
                msg = None
            raids[name] = {'composition': composition,
                           'size': int(size),
                           'disk_ratio': disk_ratio,
                           'status': status[1:-1],
                           'msg': msg
                           }
        return raids
    
    @tools.delay_cache(60) # 1 min cached
    def get_state(self, cmd_exec):
        state = OK
        raid_status = self._get_raid_status(cmd_exec)
        msgs = []
        for raid_name in raid_status:
            raid_s = raid_status[raid_name]
            if raid_s['msg']:
                msgs.append('%s: %s' % (raid_name, raid_s['msg']))
                state = WARNING
            for disk_state in raid_s['status']:
                if disk_state != 'U':
                    state = CRITICAL
                    break
        return StateValue(state, '\n'.join(msgs))

class smart(HostService):
    'Retrieve device S.M.A.R.T. status, for Hard Drive failure, ...'
    cmd_line = '/usr/sbin/smartctl'
    
    def _get_smart_data(self, result):
        rows = result.split('\n')
        for id, row in enumerate(rows):
            if row == '=== START OF READ SMART DATA SECTION ===':
                return rows[id+1:]
        return rows

    def _get_devices(self, cmd_exec):
        result = cmd_exec(['sudo', self.cmd_line, '--scan'])
        devices = {}
        for row in result.split('\n'):
            if row == '':
                break
            device, txt = row.split(' -d ', 1)
            dev_type = txt.split(' ')[0]
            devices[device] = dev_type
        return devices
    
    def _get_device_nb_errors(self, cmd_exec, devicename, power_on_hours=None):
        result = cmd_exec(['sudo', self.cmd_line, '-l', 'error', devicename])
        smart_data = self._get_smart_data(result)
        res = smart_data[1].split(': ')
        msg_rows = []
        last_error_days = None
        if len(res) > 1:
            nb_error = int(res[1].split(' ')[0])
            for line in smart_data[2:]:
                if line[:6] != 'Error ':
                    continue
                error_time = line.split(': ')[1]
                error_hour = int(error_time.split(' ')[0])
                if power_on_hours is not None:
                    days = round(float(power_on_hours - error_hour)/24)
                    if last_error_days is None:
                        last_error_days = days
                    error_time = '%u days ago' % days
                msg_rows.append('Error %s: %s' % (line.split(' ',3)[1], error_time))
            return nb_error, '\n'.join(msg_rows), last_error_days
        return 0, '', last_error_days
    
    def _get_device_attributes(self, cmd_exec, devicename):
        result = cmd_exec(['sudo', self.cmd_line, '-A', devicename])
        smart_data = self._get_smart_data(result)
        attributes = {}
        for row in smart_data[3:]:
            if row == '':
                break
            id, name, flag, value, worst, thresh, type, updated, when_failed, raw_value = row.split(None, 9)
            attributes[name] = {'flag': flag,
                                'value': int(value),
                                'thresh': int(thresh),
                                'type': type,
                                'updated': updated,
                                'when_failed':when_failed,
                                'raw_value':raw_value,
                                }
        return attributes
    
    @tools.delay_cache(300) # 5 min cached    
    def get_state(self, cmd_exec):
        state = OK
        message = ''
        if not cmd_exec.file_exists(self.cmd_line):
            print('%s not found ! Can not check for update !' % self.cmd_line)
            return StateValue(UNKNOWN, 'smartctl not found !') 
        devices = self._get_devices(cmd_exec)
        for devicename in devices:
            attributes = self._get_device_attributes(cmd_exec, devicename)
            attributes_in_error = ['%s: %s' % (a, v['raw_value']) for a, v in attributes.items() if a.lower().find('error') != -1 and int(v['raw_value'].split()[0]) > 0]
            power_on_hours = attributes.get('Power_On_Hours', None)
            if power_on_hours:
                power_on_hours = int(power_on_hours['raw_value'])
            nb_error, msg, last_error_days = self._get_device_nb_errors(cmd_exec, devicename, power_on_hours)

            if nb_error or attributes_in_error:
                message_array = ['%s Errors:%s' % (devicename, nb_error)] + attributes_in_error + [msg]
                if last_error_days is not None:
                    if last_error_days < 10:
                        state = CRITICAL
                    elif last_error_days < 30:
                        state = WARNING
                message = '\n'.join(message_array)

        return StateValue(state, message)

class linux_updates(HostService):
    def _get_update_availables(self, cmd_exec):
        # apt-get install update-notifier-common
        cmd_line = '/usr/lib/update-notifier/apt-check'
        if not cmd_exec.file_exists(cmd_line):
            cmd_line2 = '/usr/bin/apt-list-update.sh'
            if not cmd_exec.file_exists(cmd_line2):
                print('%s and %s not found ! Can not check for update !' % (cmd_line, cmd_line2))
                return None
            cmd_line = cmd_line2
        result = cmd_exec([cmd_line]).split(';')
        updates = {}
        updates['normal'] = int(result[0])
        updates['security'] = int(result[1])
        return updates

    @tools.delay_cache(300) # 5 min cached
    def get_state(self, cmd_exec):
        updates = self._get_update_availables(cmd_exec)
        if updates is None:
            return StateValue(UNKNOWN, 'apt-check not found!')
        messages = []
        if updates['normal']:
            messages.append('Normal: %s' % updates['normal'])
        if updates['security'] > 0:
            messages.append('Security: %s' % updates['security'])
        state = OK
        if updates['security'] > 0:
            state = CRITICAL    
        elif updates['normal'] > 0:
            state = WARNING
        return StateValue(state, '\n'.join(messages))

class linux_version(HostService):
    warning_below_days = 100
    version_validity = {'Ubuntu': [
                            {'version':'8.04',
                             'validity':'expired'},
                            {'version':'8.10',
                             'validity':'expired'},
                            {'version':'9.04',
                             'validity':'expired'},
                            {'version':'9.10',
                             'validity':'expired'},
                            {'version':'10.04',
                             'validity':'expired'},
                            {'version':'10.10',
                             'validity':'expired'},
                            {'version':'11.04',
                             'validity':'expired'},
                            {'version':'11.10',
                             'validity':'expired'},
                            {'version':'12.04',
                             'validity':'expired'},
                            {'version':'12.10',
                             'validity':'expired'},
                            {'version':'13.04',
                             'validity':'expired'},
                            {'version':'13.10',
                             'validity':'expired'},
                            {'version':'14.04',
                             'validity':'2019-04-30'},
                            {'version':'14.10',
                             'validity':'2015-07-23'},
                            {'version':'15.04',
                             'validity':'2016-02-04'},
                            {'version':'15.10',
                             'validity':'2016-07-28'},
                            {'version':'16.04',
                             'validity':'2021-04'},
                            {'version':'16.10',
                             'validity':'2017-07-20'},
                            {'version':'17.04',
                             'validity':'2018-01-13'},
                            {'version':'17.10',
                             'validity':'2018-07-19'},
                            {'version':'18.04',
                             'validity':'2023-04'},
                            {'version':'18.10',
                             'validity':'2019-07-18'},
                            {'version':'19.04',
                             'validity':'2020-01'},
                            {'version':'19.10',
                             'validity':'2020-07'},
                            {'version':'20.04',
                             'validity':'2025-04'},
                            {'version':'21.10',
                             'validity':'2022-07'},
                            {'version':'22.04',
                             'validity':'2027-04'},
                                   ],
                        'Debian': [
                            {'codename':'slink',
                             'validity':'2000-10-30'},
                            {'codename':'potato',
                             'validity':'2003-06-30'},
                            {'codename':'woody',
                             'validity':'2006-06-30'},
                            {'codename':'sarge',
                             'validity':'2008-03-31'},
                            {'codename':'etch',
                             'validity':'2010-02-15'},
                            {'codename':'lenny',
                             'validity':'2012-02-06'},
                            {'codename':'squeeze',
                             'validity':'2016-02-29'},
                            {'codename':'wheezy',
                             'validity':'2018-05'},
                            {'codename':'jessie',
                             'validity':'2020-04'},
                            {'codename':'stretch',
                             'validity':'2022-06'},
                            {'codename':'buster',
                             'validity':'2024-01'},
                            {'codename':'bullseye',
                             'validity':'2026-01'},
                            {'codename':'bookworm',
                             'validity':'2028-01'},
                            {'codename':'trixie',
                             'validity':'2030-01'},
                            ],
                        'LinuxMint': [
                            {'version':'5',
                             'validity': '2011-04'},
                            {'version':'6',
                             'validity': '2010-04'},
                            {'version':'7',
                             'validity': '2010-10'},
                            {'version':'8',
                             'validity': '2011-04'},
                            {'version':'9',
                             'validity': '2013-04'},
                            {'version':'10',
                             'validity': '2012-04'},
                            {'version':'11',
                             'validity': '2012-10'},
                            {'version':'12',
                             'validity': '2013-04'},
                            {'version':'13',
                             'validity': '2017-04'},
                            {'version':'14',
                             'validity': '2014-05'},
                            {'version':'15',
                             'validity': '2014-01'},
                            {'version':'16',
                             'validity': '2014-07'},
                            {'version':'17',
                             'validity': '2019-04'},
                            {'version':'17.1',
                             'validity': '2019-04'},
                            {'version':'17.2',
                             'validity': '2019-04'},
                            {'version':'17.3',
                             'validity': '2019-04'},
                            {'version':'18',
                             'validity': '2021-01'},
                            {'version':'18.1',
                             'validity': '2021-01'},
                            {'version':'18.2',
                             'validity': '2021-01'},
                            {'version':'18.3',
                             'validity': '2021-01'},
                            {'version':'19.1',
                             'validity': '2023-01'},
                            {'version':'19.2',
                             'validity': '2023-01'},
                            {'version':'19.3',
                             'validity': '2023-01'},
                            {'version':'20',
                             'validity': '2025-04'},
                            {'version':'20.1',
                             'validity': '2025-04'},
                            {'version':'20.2',
                             'validity': '2025-04'},
                            {'version':'20.3',
                             'validity': '2025-04'},
                            ]
                        }
    version_validity['Raspbian'] = version_validity['Debian']
    
    def _get_version_details(self, cmd_exec):
        cmd_line = '/usr/bin/lsb_release'
        if not cmd_exec.file_exists(cmd_line):
            print('%s not found ! Can not check for version !' % cmd_line)
            return None 
        result = cmd_exec([cmd_line, '-a'])
        data = {}
        for row in result.split('\n'):
            row_sp = row.split(':', 1)
            if len(row_sp) != 2:
                continue
            property, value = row_sp
            value = value.strip()
            data[property] = value
        return data
        
    @tools.delay_cache(3600) # 1h cached
    def get_state(self, cmd_exec):
        data = self._get_version_details(cmd_exec)
        if data is None:
            return StateValue(UNKNOWN, 'lsb_release not found !')
        if 'Description' not in data:
            return StateValue(UNKNOWN, 'Version not found !')
        message = data['Description']
        if 'Distributor ID' not in data or 'Release' not in data or 'Codename' not in data:
            return StateValue(UNKNOWN, message)
        distribution = data['Distributor ID']
        release = data['Release']
        codename = data['Codename']
        if distribution not in self.version_validity:
            return StateValue(UNKNOWN, message)
        version_validities = self.version_validity[distribution]
        validity = None
        for version_validity in version_validities:
            if 'version' in version_validity:
                if version_validity['version'] != release:
                    continue
                validity = version_validity['validity']
                break
            if 'codename' in version_validity:
                if version_validity['codename'] != codename:
                    continue
                validity = version_validity['validity']
                break
                    
        if validity is None:
            return StateValue(UNKNOWN, message)
        message = '%s [%s]' % (message, validity)
        if validity == 'expired':
            return StateValue(CRITICAL, message)
        validity_date = datetime.datetime.strptime(validity[:7],'%Y-%m').date()
        today = datetime.date.today()
        if validity_date <= today:
            return StateValue(CRITICAL, message)
        if (validity_date - today).days < self.warning_below_days:
            return StateValue(WARNING, message)
        return StateValue(OK, message)

class mem_usage(HostService):
    def _get_memory_details(self, cmd_exec):
        data = cmd_exec(['cat','/proc/meminfo'])
        result = {}
        for row in data.split('\n')[:-1]:
            parameter, value = row.split(':',1)
            value = value.strip()
            result[parameter] = value
        return result
        
    def get_state(self, cmd_exec):
        details = self._get_memory_details(cmd_exec)
        
        def get_amount(txt):
            return int(txt.split(' ', 1)[0])
        
        def human_readable(amount):
            i = 0
            while float(amount) / (1000**i) > 1:
                i += 1
            units = ['kB', 'MB', 'GB', 'TB', 'EB']
            if i > 0:
                i -= 1
                float(amount) / (1000**i)
            return '%i%s' % (int(float(amount) / (1000**i)), units[i]) 
        mem_total = get_amount(details['MemTotal'])
        mem_free = get_amount(details['MemFree'])
        mem_cached = get_amount(details['Cached'])
        mem_buffer = get_amount(details['Buffers'])
        mem_used = mem_total - mem_free - mem_cached - mem_buffer
        pc_used = mem_used / float(mem_total)
        
        swap_total = get_amount(details['SwapTotal'])
        swap_free = get_amount(details['SwapFree'])
        swap_used = swap_total - swap_free
        all_total = mem_total + swap_total
        all_used = mem_used + swap_used
        if swap_total > 0:
            pc_swap_used = swap_used / float(swap_total)
        
        state = OK
        if pc_used > 0.9 or ((all_used/float(all_total)) > 0.8):
            state = CRITICAL
        elif pc_used > 0.7:
            state = WARNING
        message = 'Mem: % 3i%% %s' % (round(pc_used*100), human_readable(mem_total))
        if swap_total > 0:
            message += '\nSwap: % 3i%% %s' % (round(pc_swap_used*100), human_readable(swap_total))
        return StateValue(state, message)

class reboot_needed(HostService):
    @tools.delay_cache(300) # 5 min cached
    def get_state(self, cmd_exec):
        if cmd_exec.file_exists('/var/run/reboot-required'):
            return StateValue(WARNING)
        return StateValue(OK)

class clamav(process):
    process_name = 'clamd'

class mysql_local(process):
    process_name = 'sbin/mysqld'

class amavis_local(process):
    process_name = 'sbin/amavisd'

#from pprint import pprint

"""cmd_exec = CmdLocalhost()
print 'Df: %s' % Df().get_state(cmd_exec)
print 'LOAD: %s' % LoadAvg().get_state(cmd_exec)
print 'RAID: %s' % Raid().get_state(cmd_exec)
print 'SMART: %s' % SmartHdd().get_state(cmd_exec)
"""
