import os
debug = os.path.isfile("/etc/eta-shutdown.debug")

if debug:
    logfile=open("/var/log/eta-shutdown.log", "a")
    def log(*args):
        print(args, file=logfile)
else:
    def log(*args):
        pass

