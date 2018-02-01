#FROM distribrewed/core:arm
FROM distribrewed/core:x64

#ENV ROOT_DIR=/usr/project
ENV ROOT_DIR=/opt/project
ENV PLUGIN_DIR=${ROOT_DIR}/workers

COPY requirements.txt ${TMP_DIR}/requirements.txt
RUN pip install -r ${TMP_DIR}/requirements.txt && rm -rf ${TMP_DIR}/*

ENV PYTHONPATH=${ROOT_DIR}:${PYTHONPATH}

COPY ./workers ${PLUGIN_DIR}
WORKDIR ${PLUGIN_DIR}
