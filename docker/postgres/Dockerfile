FROM postgres:17-alpine

COPY init-app-user.sh /docker-entrypoint-initdb.d/10-init-app-user.sh
RUN chmod 0755 /docker-entrypoint-initdb.d/10-init-app-user.sh
