FROM distribrewed/core:arm

ENV ROOT_DIR=/usr/project
ENV PLUGIN_DIR=${ROOT_DIR}/workers

COPY requirements.txt ${TMP_DIR}/requirements.txt
RUN pip install -r ${TMP_DIR}/requirements.txt && rm -rf ${TMP_DIR}/*

ENV PYTHONPATH=${ROOT_DIR}:${PYTHONPATH}

COPY ./workers ${PLUGIN_DIR}
WORKDIR ${PLUGIN_DIR}
