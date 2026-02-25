ARG BUILD_FROM
FROM ${BUILD_FROM}

# Ensure Python for ingress redirect server
RUN apk add --no-cache python3

# Copy integration to /opt so it is not hidden by a /data volume mount at runtime
COPY integration/homekit_architect /opt/homekit_architect/integration
COPY run.sh /run.sh
COPY ingress_redirect.py /ingress_redirect.py
RUN chmod +x /run.sh

WORKDIR /
CMD [ "/run.sh" ]
