import subprocess

def clang_format(file_path):
    command = [
        "clang-format-15",
        "-i",
        file_path
    ]
    run_command(command)
    
def run_command(command, input=None, timeout=None):
    try:
        result = subprocess.run(command, input=input, capture_output=True, text=True, timeout=timeout)
        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'timed_out': False
        }
    except subprocess.TimeoutExpired as e:
        return {
            'stdout': "timeout",
            'stderr': "timeout",
            'timed_out': True
        }
