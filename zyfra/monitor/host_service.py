import subprocess

from zyfra import ssh_session, tools
from probe_common import UNKNOWN, OK, WARNING, CRITICAL, Service, ProbeException, State

"""TODO:
- Add a probe for memory usage
- Add a probe for Free inode  ['df','-i']
- Add module failure messages to result for critical, warning, ...
- Add lsb_release -a to get linux version
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
    
    def __call__(self, cmd, raise_empty=True, shell=False):
        lnk = ssh_session.get_ssh_link(self.target, password=self.password)
        result = lnk.cmd(' '.join(cmd))
        if raise_empty and result == '':
            raise ProbeException('Empty result for CmdSsh: %s' % cmd)
        return result

class CmdLocalhost(Cmd):
    def __call__(self, cmd, raise_empty=True, shell=False):
        if shell:
            cmd = ' '.join(cmd)
        result = subprocess.check_output(cmd, shell=shell, stderr=subprocess.STDOUT)
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
        result = cmd_exec(['df','-P']) 
        mounts = {}
        for row in result.split('\n')[1:-1]:
            device, size, used_space, free_space, pc, mount_point = row.split(None, 5)
            size = int(size)
            used_space = int(used_space)
            free_space = int(free_space)
            if device in ('none', 'cgroup','udev','tmpfs','cgmfs','varrun','varlock','devshm','lrm'):
                continue
            mounts[mount_point] = {'device': device,
                                   'size': size,
                                   'used_space': used_space,
                                   'free_space': free_space,
                                   'pc': pc}
        return mounts
    
    def _str_data(self, data):
        mountpoints = data.keys()
        mountpoints.sort()
        return '\n'.join(['% 4s %s' % (data[mp]['pc'], mp) for mp in mountpoints])
    
    @tools.delay_cache(60) # 1 min cached
    def get_state(self, cmd_exec):
        state = OK
        mount_usages = self._get_mount_usages(cmd_exec)
        for mount_name, mount_usage in mount_usages.iteritems():
            free_ratio = mount_usage['free_space'] / float(mount_usage['size'])
            if free_ratio <= 0.1:
                return CRITICAL
            elif free_ratio <= 0.2:
                state = WARNING 
        return State(state, self._str_data(mount_usages))

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
        return State(state, ' - '.join(['%.2f' % l for l in loads]))

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
            return State(OK)
        return State(CRITICAL)

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
            raids[name] = {'composition': composition,
                           'size': int(size),
                           'disk_ratio': disk_ratio,
                           'status': status[1:-1]}
        return raids
    
    @tools.delay_cache(60) # 1 min cached
    def get_state(self, cmd_exec):
        state = OK
        raid_status = self._get_raid_status(cmd_exec)
        for raid_name in raid_status:
            for disk_state in raid_status[raid_name]['status']:
                if disk_state != 'U':
                    state = CRITICAL
                    break
        return State(state)

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
    
    def _get_device_nb_errors(self, cmd_exec, devicename):
        result = cmd_exec(['sudo', self.cmd_line, '-l', 'error', devicename])
        smart_data = self._get_smart_data(result)
        res = smart_data[1].split(': ')
        if len(res) > 1:
            return int(res[1])
        return 0
    
    def _get_device_attributes(self, cmd_exec, devicename):
        result = cmd_exec(['sudo', self.cmd_line, '-A', devicename])
        smart_data = self._get_smart_data(result)
        attributes = {}
        for row in smart_data[3:]:
            if row == '':
                break
            id, name, flag, value, worst, thresh, type, updated, when_failed, raw_value = row.split()
            attributes[name] = {'flag': flag,
                                'value': int(value),
                                'thresh': int(thresh),
                                'type': type,
                                'updated': updated,
                                'when_failed':when_failed,
                                'raw_value':int(raw_value),
                                }
        return attributes
    
    @tools.delay_cache(300) # 5 min cached    
    def get_state(self, cmd_exec):
        state = OK
        if not cmd_exec.file_exists(self.cmd_line):
            print '%s not found ! Can not check for update !' % self.cmd_line
            return State(UNKNOWN, 'smartctl not found !') 
        devices = self._get_devices(cmd_exec)
        for devicename in devices:
            nb_error = self._get_device_nb_errors(cmd_exec, devicename)
            if nb_error:
                state = WARNING
        return State(state)

class linux_updates(HostService):
    def _get_update_availables(self, cmd_exec):
        """result = cmd_exec(['sudo','/usr/lib/update-notifier/update-motd-updates-available']).split('\n')
        updates = {}
        if len(result) < 3:
            updates['normal'] = 0
            updates['security'] = 0
        else:
            updates['normal'] = int(result[1].split()[0])
            updates['security'] = int(result[2].split()[0])"""
        cmd_line = '/usr/lib/update-notifier/apt-check'
        if not cmd_exec.file_exists(cmd_line):
            print '%s not found ! Can not check for update !' % cmd_line
            return None 
        result = cmd_exec([cmd_line]).split(';')
        updates = {}
        updates['normal'] = int(result[0])
        updates['security'] = int(result[1])
        return updates
    
    @tools.delay_cache(300) # 5 min cached
    def get_state(self, cmd_exec):
        updates = self._get_update_availables(cmd_exec)
        if updates is None:
            return State(UNKNOWN, 'apt-check not found!')
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
        return State(state, '\n'.join(messages))

class reboot_needed(HostService):
    @tools.delay_cache(300) # 5 min cached
    def get_state(self, cmd_exec):
        if cmd_exec.file_exists('/var/run/reboot-required'):
            return State(WARNING)
        return State(OK)

class clamav(process):
    process_name = 'clamd'

#from pprint import pprint

"""cmd_exec = CmdLocalhost()
print 'Df: %s' % Df().get_state(cmd_exec)
print 'LOAD: %s' % LoadAvg().get_state(cmd_exec)
print 'RAID: %s' % Raid().get_state(cmd_exec)
print 'SMART: %s' % SmartHdd().get_state(cmd_exec)
"""

if __name__ == "__main__":
    print reboot_needed().ssh('monitor@10.0.0.10', password='dptoik87974')
#print 'reboot needed [%s]' % reboot_needed().get_state(CmdLocalhost())
#pprint(Process('auto_print', 'auto_print.py').ssh('root@10.0.0.15'))
