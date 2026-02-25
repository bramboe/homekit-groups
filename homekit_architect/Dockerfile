ARG BUILD_FROM
FROM ${BUILD_FROM}

# Ensure Python for ingress redirect server
RUN apk add --no-cache python3

# Copy bundled integration, run script, and ingress redirect server
COPY integration/ /data/integration/
COPY run.sh /run.sh
COPY ingress_redirect.py /ingress_redirect.py
RUN chmod +x /run.sh

WORKDIR /
CMD [ "/run.sh" ]
