import multiprocessing
import json
import time

def _read_pipe():
    while True:
        with open('/dev/shm/poxpipe','r') as pipe:
            data = pipe.read()
            print(data)
            #time.sleep(1)

if __name__ == '__main__':
    p = multiprocessing.Process(target=_read_pipe)
    p.start()

