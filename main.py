from verifier import verifier
import sys

if __name__ == "__main__":
    api_key = "sk-9aa6615a75aa4c80bee3ad5244d52fac"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        print("error: no input file")
        exit(1)

    v = verifier(timeout = 900)
    v.process_yaml(file_path)