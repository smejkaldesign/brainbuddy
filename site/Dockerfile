# Static site, same shape as the smejkal.design container: nginx serving
# the folder, listening on Railway's $PORT. Railway service root = site/.
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
RUN printf 'server {\n  listen RAILWAY_PORT;\n  root /usr/share/nginx/html;\n\n  add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;\n  add_header X-Content-Type-Options "nosniff" always;\n  add_header X-Frame-Options "DENY" always;\n  add_header Referrer-Policy "strict-origin-when-cross-origin" always;\n  add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;\n\n  location / {\n    try_files $uri $uri/ /index.html;\n  }\n}\n' > /tmp/default.conf.template
CMD ["sh", "-c", "sed s/RAILWAY_PORT/${PORT:-80}/ /tmp/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
EXPOSE 80
