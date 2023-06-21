# -*- coding: utf-8 -*-
# Update by: https://github.com/CokeMine/ServerStatus-Hotaru
# 依赖于psutil跨平台库：
# 支持Python版本：2.6 to 3.7
# 支持操作系统： Linux, Windows, OSX, Sun Solaris, FreeBSD, OpenBSD and NetBSD, both 32-bit and 64-bit architectures

import socket
import time
import os
import json
import psutil
from collections import deque

# 服务端 IP 或域名
SERVER = os.getenv("SERVER", "127.0.0.1")
# 服务端端口
PORT = int(os.getenv("PORT", 35601))
# 服务端定义的用户名
USER = os.getenv("USERNAME", "USER")
# 服务端定义的密码
PASSWORD = os.getenv("PASSWORD", "PASSWORD")
# 客户端上报更新间隔，单位：秒
INTERVAL = int(os.getenv("INTERVAL", 1))

# https://github.com/giampaolo/psutil/issues/1845
psutil.PROCFS_PATH = os.getenv("PROCFS_PATH", "/proc")


def check_interface(net_name):
    net_name = net_name.strip()
    invalid_name = ['lo', 'tun', 'kube', 'docker', 'vmbr', 'br-', 'vnet', 'veth']
    return not any(name in net_name for name in invalid_name)


def get_uptime():
    return int(time.time() - psutil.boot_time())


def get_memory():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return int(mem.total / 1024.0), int(mem.used / 1024.0), int(swap.total / 1024.0), int(swap.used / 1024.0)


def get_hdd():
    valid_fs = ['ext4', 'ext3', 'ext2', 'reiserfs', 'jfs', 'btrfs', 'fuseblk', 'zfs', 'simfs', 'ntfs', 'fat32', 'exfat',
                'xfs']
    disks = dict()
    size = 0
    used = 0
    for disk in psutil.disk_partitions():
        if disk.device not in disks and disk.fstype.lower() in valid_fs:
            disks[disk.device] = disk.mountpoint
    for disk in disks.values():
        usage = psutil.disk_usage(disk)
        size += usage.total
        used += usage.used
    return int(size / 1024.0 / 1024.0), int(used / 1024.0 / 1024.0)


def get_load():
    try:
        return round(psutil.getloadavg()[0], 1)
    except Exception:
        return -1.0


def get_cpu():
    return psutil.cpu_percent(interval=INTERVAL)


class Network:
    def __init__(self):
        self.rx = deque(maxlen=10)
        self.tx = deque(maxlen=10)
        self._get_traffic()

    def _get_traffic(self):
        net_in = 0
        net_out = 0
        net = psutil.net_io_counters(pernic=True)
        for k, v in net.items():
            if check_interface(k):
                net_in += v[1]
                net_out += v[0]
        self.rx.append(net_in)
        self.tx.append(net_out)

    def get_speed(self):
        self._get_traffic()
        avg_rx = 0
        avg_tx = 0
        queue_len = len(self.rx)
        for x in range(queue_len - 1):
            avg_rx += self.rx[x + 1] - self.rx[x]
            avg_tx += self.tx[x + 1] - self.tx[x]
        avg_rx = int(avg_rx / queue_len / INTERVAL)
        avg_tx = int(avg_tx / queue_len / INTERVAL)
        return avg_rx, avg_tx

    def get_traffic(self):
        queue_len = len(self.rx)
        return self.rx[queue_len - 1], self.tx[queue_len - 1]


def get_network(ip_version):
    if ip_version == 4:
        host = 'ipv4.google.com'
    elif ip_version == 6:
        host = 'ipv6.google.com'
    else:
        return False
    try:
        socket.create_connection((host, 80), 2).close()
        return True
    except Exception:
        return False


if __name__ == '__main__':
    socket.setdefaulttimeout(30)
    while True:
        try:
            print("Connecting...")
            s = socket.create_connection((SERVER, PORT))
            data = s.recv(1024).decode()
            if data.find("Authentication required") > -1:
                s.send((USER + ':' + PASSWORD + '\n').encode("utf-8"))
                data = s.recv(1024).decode()
                if data.find("Authentication successful") < 0:
                    print(data)
                    raise socket.error
            else:
                print(data)
                raise socket.error

            print(data)
            if data.find('You are connecting via') < 0:
                data = s.recv(1024).decode()
                print(data)

            timer = 0
            check_ip = 0
            if data.find("IPv4") > -1:
                check_ip = 6
            elif data.find("IPv6") > -1:
                check_ip = 4
            else:
                print(data)
                raise socket.error

            traffic = Network()
            while True:
                CPU = get_cpu()
                NetRx, NetTx = traffic.get_speed()
                NET_IN, NET_OUT = traffic.get_traffic()
                Uptime = get_uptime()
                Load = get_load()
                MemoryTotal, MemoryUsed, SwapTotal, SwapUsed = get_memory()
                HDDTotal, HDDUsed = get_hdd()

                array = {}
                if not timer:
                    array['online' + str(check_ip)] = get_network(check_ip)
                    timer = 150
                else:
                    timer -= 1 * INTERVAL

                array['uptime'] = Uptime
                array['load'] = Load
                array['memory_total'] = MemoryTotal
                array['memory_used'] = MemoryUsed
                array['swap_total'] = SwapTotal
                array['swap_used'] = SwapUsed
                array['hdd_total'] = HDDTotal
                array['hdd_used'] = HDDUsed
                array['cpu'] = CPU
                array['network_rx'] = NetRx
                array['network_tx'] = NetTx
                array['network_in'] = NET_IN
                array['network_out'] = NET_OUT

                s.send(("update " + json.dumps(array) + "\n").encode("utf-8"))
        except KeyboardInterrupt:
            raise
        except socket.error:
            print("Disconnected...")
            # keep on trying after a disconnect
            if 's' in locals().keys():
                del s
            time.sleep(3)
        except Exception as e:
            print("Caught Exception:", e)
            if 's' in locals().keys():
                del s
            time.sleep(3)
