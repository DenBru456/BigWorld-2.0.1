TARGETS=bigworld-bwmachined

ifndef BIGWORLD_INDIE
BIGWORLD_INDIE=0
endif

ifneq ($(BIGWORLD_INDIE),0)
# TODO: Currently building the server and tools RPM is only supported for 
# the BigWorld Indie package.

TARGETS+=bigworld-server bigworld-tools

endif

all:: $(TARGETS)

bigworld-bwmachined:
	./generate.py bwmachined

bigworld-server:
	python -m"compileall" ../../../res/scripts > /dev/null || /bin/true
	./generate.py server

bigworld-tools:
	python -m"compileall" ../../../tools/bwlockd > /dev/null || /bin/true
	python -m"compileall" ../ > /dev/null || /bin/true
	./generate.py tools

clean:
	rm -rf binary_rpms/*.rpm

bwmachined: bigworld-bwmachined
server: bigworld-server
tools: bigworld-tools
