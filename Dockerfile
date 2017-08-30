FROM distribrewed/core:x64

ENV PLUGIN_DIR=/workers

COPY requirements.txt ${TMP_DIR}/requirements.txt
RUN pip install -r ${TMP_DIR}/requirements.txt && rm -rf ${TMP_DIR}/*

COPY ./workers ${PLUGIN_DIR}
WORKDIR ${PLUGIN_DIR}
