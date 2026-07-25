# stage1 -- heavy compilation environment
FROM ubuntu:24.04 AS builder

# full compilation dependencies
RUN apt-get update && apt-get install -y \
    build-essential python3-pip cmake python3.12-venv git && \
    rm -rf /var/lib/apt/lists/*

COPY "build_scripts/ofiq_setup.sh" "/tmp/"
RUN chmod +x /tmp/ofiq_setup.sh && /bin/bash /tmp/ofiq_setup.sh


# stage 2 -- minimal runtime environment
FROM ubuntu:24.04 AS runtime

LABEL version="1.0"

# install only that cpp thing 
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# not sure about python3-pip python3.12-venv 

# Create the target directory inside the clean runtime image
WORKDIR /OFIQ-Project


# copying only stuff needed (test later, maybe I can chop even more stuff off)
COPY --from=builder /OFIQ-Project/build/                ./build/
COPY --from=builder /OFIQ-Project/cmake/                ./cmake/
COPY --from=builder /OFIQ-Project/conan/                ./conan/
COPY --from=builder /OFIQ-Project/data/                 ./data/
COPY --from=builder /OFIQ-Project/extern/               ./extern/
COPY --from=builder /OFIQ-Project/install_x86_64_linux/ ./install_x86_64_linux/
COPY --from=builder /OFIQ-Project/OFIQlib/              ./OFIQlib/
COPY --from=builder /OFIQ-Project/scripts/              ./scripts/
COPY --from=builder /OFIQ-Project/testing/              ./testing/

# adding selftest and evaluation to the scripts after the directory has been overwritten
COPY build_scripts/selftest.sh ./scripts

# RUN [ "/usr/bin/bash", "./scripts/selftest.sh" ]

COPY experiment_scripts/dataset_eval.sh ./scripts

ENTRYPOINT [ "/usr/bin/bash", "./scripts/dataset_eval.sh" ]
