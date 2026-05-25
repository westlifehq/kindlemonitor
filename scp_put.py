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

def scp_put(local_path, remote_path, host=None, user=None, password=None):
    if host is None:
        host = os.environ.get("FN_HOST", "192.168.31.161")
    if user is None:
        user = os.environ.get("FN_USER", "rvc")
    if password is None:
        password = os.environ.get("FN_PASSWORD", "your_fnos_password")
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
