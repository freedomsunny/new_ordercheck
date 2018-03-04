# encoding=utf-8

##############################################
#
# 每个继承unittest.TestCase的类都是一个测试用例
#
##############################################
import unittest
import json
from bin.measure import get_redis_data
from order_check.plugins.instance import Instance


class TestFunc(unittest.TestCase):
    # 每个case测试之前初始化
    def setUp(self):
        pass

    # 每个case测试之后执行
    def tearDown(self):
        pass

    # 所有case测试之前初始化
    @classmethod
    def setUpClass(cls):
        cls.redis_data = get_redis_data()

    # 所有case测试之后执行
    @classmethod
    def tearDownClass(cls):
        pass

    # 跳过某个case
    @unittest.skip("I don't want to run this case.")
    def test_skip_some(self):
        pass

    # test case. method name must start with `test_`
    def test_get_redis_data(self):
        """starting test get redis data"""
        self.assertEqual(True, isinstance(self.redis_data, str))

    # get vm_data
    def test_getvm_data(self):
        """starting test get vm data"""
        method, resource_type, token, resource_data = self.redis_data.split("++")
        self.vm_obj = Instance(data=json.loads(resource_data),
                               method=method,
                               resource_type=resource_type,
                               token=token)
        self.assertEqual(True, isinstance(self.vm_obj.get_vm_data, dict))

    # post vm data to charging
    def test_post_vm_data(self):
        """starting post vm data to charging(create order)"""
        method, resource_type, token, resource_data = self.redis_data.split("++")
        self.vm_obj = Instance(data=json.loads(resource_data),
                               method=method,
                               resource_type=resource_type,
                               token=token)
        self.assertEqual(True, isinstance(self.vm_obj.get_vm_data, dict))
        self.result = self.vm_obj.create()
        self.assertTrue(self.result)


if __name__ == '__main__':
    unittest.main()
