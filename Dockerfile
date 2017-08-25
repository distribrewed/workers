FROM distribrewed/core:x64

ENV PLUGIN_DIR=/workers \
    WORKER_PLUGIN_CLASS=TelegramWorker

COPY . ${PLUGIN_DIR}
WORKDIR ${PLUGIN_DIR}
RUN pip install -r requirements.txt
