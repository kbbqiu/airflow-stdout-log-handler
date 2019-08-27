# -*- coding: utf-8 -*-

import logging
import sys

from airflow.utils.log.file_task_handler import FileTaskHandler
from airflow.utils.log.json_formatter import JSONFormatter
from airflow.utils.log.logging_mixin import LoggingMixin


class TeeFileTaskHandler(FileTaskHandler, LoggingMixin):
    """
    TeeFileTaskHandler extends FileTaskHandler. If write_stdout
    is enabled, this handler will write to filesystem as well as stdout
    once the task is complete
    """

    def __init__(self, base_log_folder, filename_template,
                 write_stdout, json_format, json_fields):
        """
        :param base_log_folder: base folder to store logs on filesystem
        :param filename_template: file name for each task
        :param write_stdout: Boolean value to enable tasks to stdout
        :param json_format: Boolean to output logs in JSON
        :param json_fields: keys for JSON object; tagging logs
        """
        super().__init__(
            base_log_folder, filename_template)

        self.closed = False
        self.stream_handler = None
        self.log_relative_path = None
        self.mark_end_on_close = True
        self.write_stdout = write_stdout
        self.json_format = json_format
        self.json_fields = [label.strip() for label in json_fields.split(",")]

    @staticmethod
    def _clean_execution_date(execution_date):
        """
        Escape execution date so that it is safe to query
        :param execution_date: execution date of the dag run.
        """
        return execution_date.strftime("%Y_%m_%dT%H_%M_%S_%f")

    def set_context(self, ti):
        """
        Provide task_instance context to airflow task handler.
        :param ti: task instance object
        """
        super().set_context(ti)
        self.log_relative_path = self._render_filename(ti, ti.try_number)
        self.mark_end_on_close = not ti.raw

        if self.write_stdout:
            self.stream_handler = logging.StreamHandler(stream=sys.__stdout__)
            self.stream_handler.setLevel(self.level)
            if self.json_format and not ti.raw:
                self.stream_handler.setFormatter(
                    JSONFormatter(
                      self.formatter._fmt,
                      json_fields=self.json_fields,
                      extras={
                        'dag_id': str(ti.dag_id),
                        'task_id': str(ti.task_id),
                        'execution_date': self._clean_execution_date(
                            ti.execution_date),
                        'try_number': str(ti.try_number),
                        'is_airflow_dag': 'true'}))
            else:
                self.stream_handler.setFormatter(self.formatter)

    def close(self):
        # When application exits, system shuts down all handlers by
        # calling close method. Here we check if logger is already
        # closed to prevent uploading the log multiple times when
        # `logging.shutdown` is called.
        if self.closed:
            return

        if not self.mark_end_on_close:
            self.closed = True
            return

        # Case which context of the handler was not set.
        if self.stream_handler is None:
            self.closed = True
            return

        if self.write_stdout:
            # Task has finished running, write entire contents of log to stdout
            self.write_task_to_stdout()

            self.stream_handler.close()
            sys.stdout = sys.__stdout__

        super().close()

        self.closed = True

    def write_task_to_stdout(self):
        try:
            absolute_path = self.local_base + '/' + self.log_relative_path
            log_file = open(absolute_path, "r")
            contents = log_file.read()
        except IOError:
            pass

        self.stream_handler.emit(logging.makeLogRecord({
            'msg': "*TASK_LOG*\n\n" + contents,
            'log_path': absolute_path
        }))
