ARG BUILD_FROM
FROM ${BUILD_FROM}

# Copy bundled integration and run script
COPY integration/ /data/integration/
COPY run.sh /run.sh
RUN chmod +x /run.sh

WORKDIR /
CMD [ "/run.sh" ]
