# encoding=utf-8
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from order_check.cache import Backend
from order_check.plugins.instance import Instance
from order_check.plugins.routers import Routers
from order_check.plugins.floating_ips import FloatingIps
from order_check.plugins.instance_tencent import InstanceTencent
from order_check.plugins.cloud_volumes_tencent import CloudDisk
from order_check.plugins.cloud_volumes_xcloud import XcloudDisk
from order_check.plugins.port_bandwith import PortBandWith
from order_check.options import get_options
import order_check.log as logging
from tomorrow import threads

options = get_options()
LOG = logging.getLogger(__name__)

cache_obj = Backend()
charging_data_key = "charging_data"


# 线上云主机订单
@threads(10)
def instance_order(data_str):
    try:
        method, resource_type, token, resource_data = data_str.split("++")
        resource_data = json.loads(resource_data)
        instance_obj = Instance(data=resource_data,
                                method=method,
                                resource_type=resource_type,
                                token=token)
        if method == "POST":
            ret = instance_obj.create()
            # 发送订单失败，记录日志
            if not ret:
                em = "send order error. data: {0}".format(data_str)
                print em
                LOG.exception(em)
                return False
            return True

        if method == "DELETE":
            ret = instance_obj.delete()
            # 发送订单失败，记录日志
            if not ret:
                em = "send order error. data: {0}".format(data_str)
                print em
                LOG.exception(em)
                return False
            return True

        if method == "PUT":
            pass
        instance_obj.cleanup()
    except Exception as e:
        # 异常需要将数据还原
        em = "send order error. data: {0} msg: <{1}>".format(data_str,
                                                             e)
        LOG.exception(em)
        return False


# 线上路由订单
@threads(10)
def router_order(data_str):
    try:
        method, resource_type, token, resource_data = data_str.split("++")
        router_obj = Routers(data=json.loads(resource_data),
                             method=method,
                             resource_type=resource_type,
                             token=token)
        if method == "POST":
            router_obj.create()

        if method == "DELETE":
            router_obj.delete()

        if method == "PUT":
            pass
        router_obj.cleanup()
    except Exception as e:
        em = "send order error. data: {0} msg: <{1}>".format(data_str,
                                                             e)
        LOG.exception(em)
        return False


# 线上浮动IP
@threads(10)
def floating_ip_order(data_str):
    try:
        method, resource_type, token, resource_data = data_str.split("++")
        float_ip_obj = FloatingIps(data=json.loads(resource_data),
                                   method=method,
                                   resource_type=resource_type,
                                   token=token)
        if method == "POST":
            float_ip_obj.create()

        if method == "DELETE":
            float_ip_obj.delete()

        if method == "PUT":
            pass
        float_ip_obj.cleanup()
    except Exception as e:
        em = "send order error. data: {0} msg: <{1}>".format(data_str,
                                                             e)
        LOG.exception(em)
        return False


# 线上云磁盘
@threads(10)
def xcloud_volumes_order(data_str):
    try:
        method, resource_type, token, resource_data = data_str.split("++")
        volumes_order = XcloudDisk(data=json.loads(resource_data),
                                   method=method,
                                   resource_type=resource_type,
                                   token=token)
        if method == "POST":
            volumes_order.create()

        if method == "DELETE":
            volumes_order.delete()

        if method == "PUT":
            pass
        volumes_order.cleanup()
    except Exception as e:
        em = "send order error. data: {0} msg: <{1}>".format(data_str,
                                                             e)
        LOG.exception(em)
        return False


# 线上带宽更新
@threads(10)
def bandwith_order(data_str):
    try:
        method, resource_type, token, resource_data = data_str.split("++")
        resource_data = json.loads(resource_data)
        if "qos_policy_id" in resource_data.get("port").keys():
            bandwith = PortBandWith(data=resource_data,
                                    method=method,
                                    resource_type=resource_type,
                                    token=token)
            if method == "POST":
                pass

            if method == "DELETE":
                pass

            if method == "PUT":
                bandwith.update()
            bandwith.cleanup()
    except Exception as e:
        em = "send order error. data: {0} msg: <{1}>".format(data_str,
                                                             e)
        LOG.exception(em)
        return False


# 腾迅云主机
@threads(10)
def instance_tencent(data_str):
    try:
        method, resource_type, token, resource_data = data_str.split("++")
        resource_data = json.loads(resource_data)
        if "InstancePrice" not in resource_data.get("data").keys():

            tencent_instance_obj = InstanceTencent(data=resource_data,
                                                   method=method,
                                                   resource_type=resource_type,
                                                   token=token)

            if method == "POST":
                tencent_instance_obj.create()

            if method == "DELETE":
                tencent_instance_obj.delete()

            if method == "PUT":
                pass
            tencent_instance_obj.cleanup()
    except Exception as e:
        em = "send order error. data: {0} msg: <{1}>".format(data_str,
                                                             e)
        LOG.exception(em)
        return False


# 腾讯云磁盘
@threads(10)
def volumes_tencent(data_str):
    try:
        method, resource_type, token, resource_data = data_str.split("++")
        resource_data = json.loads(resource_data)
        # 云硬盘询价时的data数据为int类型（价格）不做处理
        if not isinstance(resource_data.get("data"), (float, int)):
            tencent_clouddisk_obj = CloudDisk(data=resource_data,
                                              method=method,
                                              resource_type=resource_type,
                                              token=token)

            if method == "POST":
                tencent_clouddisk_obj.create()

            if method == "DELETE":
                tencent_clouddisk_obj.delete()

            if method == "PUT":
                pass
            tencent_clouddisk_obj.cleanup()
    except Exception as e:
        em = "send order error. data: {0} msg: <{1}>".format(data_str,
                                                             e)
        LOG.exception(em)
        return False


def get_redis_data(key=charging_data_key):
    data_str = cache_obj.s_pop(key=key)
    if data_str:
        return data_str
    return None


if __name__ == '__main__':
    while True:
        data_str = get_redis_data()
        try:
            if data_str:
                method, resource_type, token, data = data_str.split("++")
                if resource_type == "instance":
                    instance_order(data_str)

                elif resource_type == "instance_tencent":
                    instance_tencent(data_str)

                elif resource_type == "volumes_tencent":
                    volumes_tencent(data_str)

                elif resource_type == "router":
                    router_order(data_str)

                elif resource_type == "float_ip":
                    floating_ip_order(data_str)

                elif resource_type == "volumes_xcloud":
                    xcloud_volumes_order(data_str)

                elif resource_type == "port":
                    bandwith_order(data_str)

                time.sleep(0.1)
        except Exception as e:
            # 发送失败，记录日志
            em = "send order error. data: {0} msg: <{1}>".format(data_str,
                                                                 e)
            print em
            LOG.exception(em)
