# encoding=utf-8
import json

from order_check.options import get_options
from order_check.plugins.manageresource import OrderBase, PostData
from order_check.utils import get_http, post_http, getDateTimeFromISO8601String
import order_check.log as logging

options = get_options()
LOG = logging.getLogger(__name__)


class InitCloudDiskData(object):
    """解析云硬盘数据"""
    def __init__(self, data):
        # 与哪台云主机关联
        self.uInstanceId = data.get("uInstanceId")
        # 单位GB
        self.disk_size = data.get("storageSize")
        # 支付类型
        self.pay_mode = data.get("payMode")
        self.zone = data.get("zone")
        self.storge_type = data.get("storageType")
        self.start_time = data.get("createTime")
        self.end_time = data.get("deadlineTime")


class CloudDisk(OrderBase):
    def __init__(self, data, method, resource_type, token):
        """
        data: the request data(get from redis types string)
        """
        super(CloudDisk, self).__init__()
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
                # `volumeid` is resource id
                self.disk_id = self.data.get("data").get("volumeid")
                self.code = self.data.get("code")
                self.res_msg = self.data.get("message")
            except:
                em = "get data may be not we need. method: {0} resource type: {1} data: {2}".format(method,
                                                                                                    resource_type,
                                                                                                    self.data)
                LOG.exception(em)

    @property
    def volumes_data(self):
        # get vm data from `api_gateway`
        url = options.api_gateway_url + "/cloud/tencent/volume?region={0}&volumeid={1}".format(self.region,
                                                                                               self.disk_id)
        result = get_http(url=url, headers=self.headers).json()
        if result.get("code") != 200:
            em = "get volumes data from tencent error. id: <{0}> msg: <{1}>".format(self.disk_id,
                                                                                result.get("message")
                                                                                )
            LOG.exception(em)
            return {}
        return result.get("data")[0]

    @property
    def post_data(self):
        # return post data
        volumes_data = self.volumes_data
        if not volumes_data:
            return {}
        volumes_data_obj = InitCloudDiskData(volumes_data)
        # 获取价格
        url = options.api_gateway_url + "/cloud/tencent/volumeprice"
        req_data = {"region": self.region,
                    "zone": volumes_data_obj.zone,
                    "type": volumes_data_obj.storge_type,
                    "size": volumes_data_obj.disk_size,
                    "period": self.period
                    }
        req_data = json.dumps(req_data)
        result = post_http(url=url, data=req_data, headers=self.headers).json()
        if result.get("code") != 200:
            em = "get price error from tencent. msg: {0}".format(result.get("message"))
            LOG.exception(em)
            return False
        # 构建post数据
        self.base_data.resource_id = self.disk_id
        self.base_data.resources = {"cloud_disk": volumes_data_obj.disk_size
                                    }
        self.base_data.timestamp = volumes_data_obj.start_time
        self.base_data.end_time = volumes_data_obj.end_time
        # 云磁盘价格目前是以分为单位
        self.base_data.money = result.get("data")
        self.base_data.resource_from_provider = "tencent"
        self.base_data.resource = "cloud_disk"
        self.base_data.resource_from = self.region
        self.base_data.order_type = "2"
        self.base_data.tenant_id = self.user_data.get("project").get("id")
        self.base_data._context_project_name = self.user_data.get("project").get("name")
        self.base_data._context_user_name = self.user_data.get("user").get("name")
        self.base_data.user_id = self.user_data.get("user").get("id")
        order_data = PostData(self.base_data)
        return order_data.post_data

    def create(self):
        return self.create_order(self.post_data, token=self.token, order_type="tencent")

    def update(self):
        pass

    def delete(self):
        return self.end_order(self.base_data.resource_id, token=self.token, order_type="tencent")
