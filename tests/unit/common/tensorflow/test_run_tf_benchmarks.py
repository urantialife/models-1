#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: EPL-2.0
#

import fnmatch
import os
import pytest
import re
import sys

from mock import MagicMock, patch

from benchmarks.common.tensorflow.run_tf_benchmark import ModelBenchmarkUtil
from test_utils import platform_config
from test_utils.io import parse_csv_file


def parse_model_args_file():
    """
    Gets test args from the tf_model_args.txt file to use as parameters
    for testing model benchmarking scripts.  The file has a
    run_tf_benchmarks.py command with args with the corresponding run command
    that should get called from model_init.py
    """
    current_dir = os.path.dirname(os.path.realpath(__file__))
    csv_file_path = os.path.join(current_dir, "tf_model_args.txt")
    return parse_csv_file(csv_file_path, 2)


def delete_env_var(env_var):
    if env_var in os.environ:
        del os.environ[env_var]


def clear_kmp_env_vars():
    """
    Clear env vars to ensure that previously set values are not affecting the next test
    """
    delete_env_var("KMP_SETTINGS")
    delete_env_var("KMP_BLOCKTIME")
    delete_env_var("KMP_AFFINITY")
    delete_env_var("KMP_HW_SUBSET")
    delete_env_var("OMP_NUM_THREADS")


# Get test args to use as parameters for test_run_benchmark
test_arg_values = parse_model_args_file()


@pytest.mark.parametrize("test_args,expected_cmd", test_arg_values)
@patch("os.mkdir")
@patch("shutil.rmtree")
@patch("os.listdir")
@patch("os.path.isdir")
@patch("os.path.isfile")
@patch("os.path.exists")
@patch("os.stat")
@patch("os.chdir")
@patch("os.remove")
@patch("common.platform_util.os")
@patch("common.platform_util.system_platform")
@patch("common.platform_util.subprocess")
@patch("common.base_model_init.BaseModelInitializer.run_command")
def test_run_benchmark(mock_run_command, mock_subprocess, mock_platform,
                       mock_os, mock_remove, mock_chdir, mock_stat, mock_path_exists, mock_is_file, mock_is_dir,
                       mock_listdir, mock_rmtree, mock_mkdir, test_args, expected_cmd):
    """
    Runs through executing the specified run_tf_benchmarks.py command from the
    test_args and verifying that the model_init file calls run_command with
    the expected_cmd string.
    """
    os.environ["PYTHON_EXE"] = "python"
    mock_path_exists.return_value = True
    mock_is_dir.return_value = True
    mock_is_file.return_value = True
    mock_stat.return_value = MagicMock(st_nlink=0)
    parse_model_args_file()
    mock_listdir.return_value = True
    clear_kmp_env_vars()
    platform_config.set_mock_system_type(mock_platform)
    platform_config.set_mock_os_access(mock_os)
    platform_config.set_mock_lscpu_subprocess_values(mock_subprocess)
    test_args = re.sub(" +", " ", test_args)        # get rid of extra spaces in the test_args string
    expected_cmd = re.sub(" +", " ", expected_cmd)  # get rid of extra spaces in the expected_cmd string
    test_arg_list = test_args.split(" ")
    with patch.object(sys, "argv", test_arg_list):
        model_benchmark = ModelBenchmarkUtil()
        model_benchmark.main()
    assert len(mock_run_command.call_args_list) == 1
    call_args = mock_run_command.call_args_list[0][0][0]
    # python3 argparse parses things in different order than python2
    # we'll check that the args are all there though
    for actual_arg, expected_arg in zip(sorted(call_args.split()), sorted(expected_cmd.split())):
        # use fnmatch in case we have file names with wildcards (like timestamps in output files)
        assert fnmatch.fnmatch(actual_arg, expected_arg), \
            "Expected: {}\nActual: {}".format(expected_cmd, call_args)
