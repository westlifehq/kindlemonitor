#!/usr/bin/env python3
import sys
import pexpect

def scp_put(local_path, remote_path, host="192.168.31.161", user="rvc", password="your_password"):
    scp_cmd = f"scp -o StrictHostKeyChecking=no {local_path} {user}@{host}:{remote_path}"
    child = pexpect.spawn(scp_cmd, timeout=30, encoding='utf-8')
    try:
        index = child.expect([
            'Are you sure you want to continue connecting',
            '[pP]assword:',
            pexpect.EOF,
            pexpect.TIMEOUT
        ])
        
        if index == 0:
            child.sendline('yes')
            index = child.expect(['[pP]assword:', pexpect.EOF, pexpect.TIMEOUT])
            
        if index == 1 or (index == 0 and 'password' in child.after.lower()):
            child.sendline(password)
        elif index >= 2:
            print(f"SCP Connection failed: {child.before}", file=sys.stderr)
            sys.exit(1)
            
        child.expect(pexpect.EOF)
        print("SCP Transfer Complete")
    except pexpect.TIMEOUT:
        print(f"SCP Timeout occurred. Before:\n{child.before}\nAfter:\n{child.after}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"SCP Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: scp_put.py <local_path> <remote_path>", file=sys.stderr)
        sys.exit(1)
    scp_put(sys.argv[1], sys.argv[2])
