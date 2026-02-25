ARG BUILD_FROM
FROM ${BUILD_FROM}

# Copy bundled integration into image (not under /data: Supervisor mounts /data for persistent storage and overwrites it)
COPY integration/ /usr/share/homekit_architect/
COPY run.sh /run.sh
COPY server.py /server.py
RUN chmod +x /run.sh

WORKDIR /
CMD [ "/run.sh" ]
