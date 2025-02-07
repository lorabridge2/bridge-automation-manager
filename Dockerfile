FROM python:3.11-alpine AS build

WORKDIR /home/decompression
RUN apk add --no-cache gcc libc-dev g++
RUN pip install --no-cache-dir pipenv
COPY Pipfile* ./
RUN pipenv install --system --clear

FROM python:3.11-alpine
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/lib/libstdc++* /usr/lib/
WORKDIR /home/decompression
COPY . .

RUN mkdir /home/decompression/backup && chown -R 1337:1337 /home/decompression/backup
VOLUME /home/decompression/backup

USER 1337:1337
ENTRYPOINT [ "python3", "decompression.py"]
