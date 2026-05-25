import sys
import pexpect
import os

# ---------- 加载 .env 环境变量 ----------
def load_env(env_path=".env"):
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass

load_env(".env")

def ssh_run(command, host=None, user=None, password=None):
    if host is None:
        host = os.environ.get("FN_HOST", "192.168.31.161")
    if user is None:
        user = os.environ.get("FN_USER", "rvc")
    if password is None:
        password = os.environ.get("FN_PASSWORD", "your_fnos_password")
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no {user}@{host}"
    child = pexpect.spawn(ssh_cmd, timeout=30, encoding='utf-8')
    
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
            print(f"Connection failed: {child.before}", file=sys.stderr)
            sys.exit(1)
            
        # Expect the main shell prompt
        child.expect(r'rvc@.*[\$#]\s*')
        
        # Turn off echo
        child.sendline('stty -echo')
        child.expect(r'rvc@.*[\$#]\s*')
        
        # Send command
        child.sendline(command)
        
        # Wait for the command to finish and prompt to return
        child.expect(r'rvc@.*[\$#]\s*')
        
        output = child.before
        if output:
            print(output.rstrip('\r\n'))
            
        # Close connection cleanly
        child.sendline('exit')
        child.expect(pexpect.EOF)
    except pexpect.TIMEOUT:
        print(f"Timeout occurred. Before:\n{child.before}\nAfter:\n{child.after}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ssh_run.py <command>", file=sys.stderr)
        sys.exit(1)
    cmd = sys.argv[1]
    ssh_run(cmd)
