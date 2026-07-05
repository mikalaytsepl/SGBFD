FROM ubuntu:24.04

LABEL version="1.0"

COPY build_scripts/ofiq_setup.sh /tmp/ofiq_setup.sh
COPY build_scripts/selftest.sh /tmp/selftest.sh

# running setup 
RUN chmod +x /tmp/ofiq_setup.sh /tmp/selftest.sh && \
    sh /tmp/ofiq_setup.sh

# entrypoint will run conformance tests to check if container is ready to process images
ENTRYPOINT [ "/tmp/selftest.sh" ]