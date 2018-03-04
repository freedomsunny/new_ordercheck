# encoding=utf-8
import json

from order_check.options import get_options
from order_check.plugins.manageresource import OrderBase, PostData
from order_check.utils import get_http, post_http, getDateTimeFromISO8601String
import order_check.log as logging

options = get_options()
LOG = logging.getLogger(__name__)


class InitCvmData(object):
    """解析虚拟机数据"""
    def __init__(self, data):
        self.zone = data.get("Placement").get("Zone")
        self.temptype = data.get("InstanceType")
        self.imageid = data.get("ImageId")
        self.PublicIpAssigned = data.get("PublicIpAddresses")
        self.PublicIpBandwidth = data.get("InternetAccessible").get("InternetMaxBandwidthOut")
        self.vcpu = data.get("CPU")
        self.memory = data.get("Memory")
        self.disk = data.get("SystemDisk").get("DiskSize")
        self.start_time = getDateTimeFromISO8601String(data.get("CreatedTime"))
        self.end_time = getDateTimeFromISO8601String(data.get("ExpiredTime"))


class InstanceTencent(OrderBase):
    def __init__(self, data, method, resource_type, token):
        """
        data: the request data(get from redis types string)
        """
        super(InstanceTencent, self).__init__()
        self.data = data
        self.method = method
        self.resource_type = resource_type
        self.token = token
        self.user_data = self.user_info(token=self.token)
        self.headers = {"X-Auth-Token": self.token,
                        "Content-Type": "application/json",
                        "TxToken": self.user_data.get("TxToken"),
                        "TxKey": self.user_data.get("TxKey"),
                        "TxId": self.user_data.get("TxId")}
        if self.method == "POST" or self.method == "PUT":
            try:
                self.region = self.data.get("data").get("region")
                # how long use
                self.period = self.data.get("data").get("period")
                # `cvm_id` is resource id
                self.cvm_id = self.data.get("data").get("instanceid")
                self.code = self.data.get("code")
                self.res_msg = self.data.get("message")
            except:
                em = "get data may be not we need. method: {0} resource type: {1} data: {2}".format(method,
                                                                                                    resource_type,
                                                                                                    self.data)
                LOG.exception(em)

    @property
    def vm_data(self):
        # get vm data from `api_gateway`
        url = options.api_gateway_url + "/cloud/tencent/instance?region={0}&instanceid={1}".format(self.region,
                                                                                                   self.cvm_id)

        result = get_http(url=url, headers=self.headers).json()
        if result.get("code") != 200:
            em = "get instance from tencent error. id: <{0}> msg: <{1}>".format(self.cvm_id,
                                                                                result.get("message")
                                                                                )
            LOG.exception(em)
            return {}
        return result.get("data")[0]

    @property
    def post_data(self):
        # return post data
        vm_data = self.vm_data
        if not vm_data:
            return {}
        vm_data_obj = InitCvmData(vm_data)
        # 获取价格
        url = options.api_gateway_url + "/cloud/tencent/instanceprice"
        req_data = {"region": self.region,
                    "zone": vm_data_obj.zone,
                    "temptype": vm_data_obj.temptype,
                    "imageid": vm_data_obj.imageid,
                    "PublicIpAssigned": True if vm_data_obj.PublicIpAssigned else False,
                    "PublicIpBandwidth": 1,
                    "period": self.period
                    }
        data = json.dumps(req_data)
        result = post_http(url=url, data=data, headers=self.headers).json()
        if result.get("code") != 200:
            em = "get price error from tencent. msg: {0}".format(result.get("message"))
            LOG.exception(em)
            return False
        # 得到虚拟机价格
        total_price = 0
        price_data = result.get('data')
        for types in price_data:
            total_price += price_data.get(types).get("DiscountPrice")
        # 构建post数据
        self.base_data.resources = {"instance": 1,
                                    # "vcpus": vm_data_obj.vcpu,
                                    # "disk_gb": vm_data_obj.disk,
                                    # "floating_ip": vm_data_obj.PublicIpAssigned[0] if vm_data_obj.PublicIpAssigned else ""
                                    }
        self.base_data.resource_id = self.cvm_id
        self.base_data.timestamp = vm_data_obj.start_time
        self.base_data.end_time = vm_data_obj.end_time
        self.base_data.money = total_price
        self.base_data.resource_from_provider = "tencent"
        self.base_data.resource = "instance"
        self.base_data.resource_from = self.region
        self.base_data.order_type = "2"
        self.base_data.tenant_id = self.user_data.get("project").get("id")
        self.base_data._context_project_name = self.user_data.get("project").get("name")
        self.base_data._context_user_name = self.user_data.get("user").get("name")
        self.base_data.user_id = self.user_data.get("user").get("id")
        order_data = PostData(self.base_data)
        return order_data.post_data

    def create(self):
        post_data = self.post_data
        if not post_data:
            em = "get tencent post data error."
            LOG.exception(em)
            return False
        return self.create_order(self.post_data, order_type="tencent", token=self.token)

    def update(self):
        pass

    def delete(self):
        pass
        # return self.end_order(self.base_data.resource_id)
