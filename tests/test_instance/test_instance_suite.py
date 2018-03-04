# -*- coding: utf-8 -*-
import sys
sys.path.append("/root/new_ordercheck")
import unittest
from tests.test_instance.test_instance import TestFunc

if __name__ == '__main__':
    suite = unittest.TestSuite()

    tests = [TestFunc("test_get_redis_data"),
             TestFunc("test_getvm_data"),
             TestFunc("test_post_vm_data")
             ]
    suite.addTests(tests)
    #
    # with open('/var/log/unit_test_{0}.log'.format(__file__.split(".")[0]), 'a+') as f:
    #     runner = unittest.TextTestRunner(stream=f, verbosity=2)
    #     runner.run(suite)

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

