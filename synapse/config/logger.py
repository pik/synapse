# -*- coding: utf-8 -*-
# Copyright 2014-2016 OpenMarket Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ._base import Config
from synapse.util.logcontext import LoggingContextFilter
from twisted.python.log import PythonLoggingObserver
import logging
import logging.config
import yaml
from string import Template
import os
import signal
from synapse.util.debug import debug_deferreds


DEFAULT_LOG_CONFIG = Template("""
version: 1

formatters:
  precise:
   format: '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(request)s\
- %(message)s'

filters:
  context:
    (): synapse.util.logcontext.LoggingContextFilter
    request: ""

handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    formatter: precise
    filename: ${log_file}
    maxBytes: 104857600
    backupCount: 10
    filters: [context]
    level: INFO
  console:
    class: logging.StreamHandler
    formatter: precise
    filters: [context]

loggers:
    synapse:
        level: INFO

    synapse.storage.SQL:
        level: INFO

root:
    level: INFO
    handlers: [file, console]
""")


class LoggingConfig(Config):

    def read_config(self, config):
        self.verbosity = config.get("verbose", 0)
        self.log_config = self.abspath(config.get("log_config"))
        self.log_file = self.abspath(config.get("log_file"))
        if config.get("full_twisted_stacktraces"):
            debug_deferreds()

    def default_config(self, config_dir_path, server_name, **kwargs):
        log_file = self.abspath("homeserver.log")
        log_config = self.abspath(
            os.path.join(config_dir_path, server_name + ".log.config")
        )
        return """
        # Logging verbosity level.
        verbose: 0

        # File to write logging to
        log_file: "%(log_file)s"

        # A yaml python logging config file
        log_config: "%(log_config)s"

        # Stop twisted from discarding the stack traces of exceptions in
        # deferreds by waiting a reactor tick before running a deferred's
        # callbacks.
        # full_twisted_stacktraces: true
        """ % locals()

    def read_arguments(self, args):
        if args.verbose is not None:
            self.verbosity = args.verbose
        if args.log_config is not None:
            self.log_config = args.log_config
        if args.log_file is not None:
            self.log_file = args.log_file

    def add_arguments(cls, parser):
        logging_group = parser.add_argument_group("logging")
        logging_group.add_argument(
            '-v', '--verbose', dest="verbose", action='count',
            help="The verbosity level."
        )
        logging_group.add_argument(
            '-f', '--log-file', dest="log_file",
            help="File to log to."
        )
        logging_group.add_argument(
            '--log-config', dest="log_config", default=None,
            help="Python logging config file"
        )

    def generate_files(self, config):
        log_config = config.get("log_config")
        if log_config and not os.path.exists(log_config):
            with open(log_config, "wb") as log_config_file:
                log_config_file.write(
                    DEFAULT_LOG_CONFIG.substitute(log_file=config["log_file"])
                )

    def setup_logging(self):
        setup_logging(self.log_config, self.log_file, self.verbosity)


def setup_logging(log_config=None, log_file=None, verbosity=None):
    log_format = (
        "%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(request)s"
        " - %(message)s"
    )
    if log_config is None:
        logging.config.dictConfig(yaml.load(DEFAULT_LOG_CONFIG.template))
    else:
        with open(log_config, 'r') as f:
            logging.config.dictConfig(yaml.load(f))

    observer = PythonLoggingObserver()
    observer.start()
