from verifier import verifier
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        print("error: no input file")
        exit(1)

    v = verifier(timeout = 900)
    v.process_yaml(file_path)
