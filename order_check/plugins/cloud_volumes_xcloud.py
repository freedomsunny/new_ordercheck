# encoding=utf-8
import json

from order_check.options import get_options
from order_check.plugins.manageresource import OrderBase, PostData
from order_check.utils import  getDateTimeFromISO8601String, get_now_time
import order_check.log as logging

options = get_options()
LOG = logging.getLogger(__name__)

class XcloudDisk(OrderBase):
    def __init__(self, data, method, resource_type, token):
        """
        data: the request data(get from redis types string)
        """
        super(XcloudDisk, self).__init__()
        self.data = data
        self.method = method
        self.resource_type = resource_type
        self.token = token
        self.user_data = self.user_info(token=self.token)
        if self.method == "POST" or self.method == "PUT":
            try:
                self.base_data.resource_id = self.data.get("volume").get("id")
                self.base_data.resource = self.data.get("volume").get("displayName")
                self.used = self.data.get("volume").get("size")
                self.zone = self.data.get("volume").get("availabilityZone")
                # start time
                self.base_data.timestamp = getDateTimeFromISO8601String(self.data.get("volume").get("createdAt"))
                self.headers = {"X-Auth-Token": self.token,
                                "Content-Type": "application/json"}
            except:
                em = "get data may be not we need. method: {0} resource type: {1} data: {2}".format(method,
                                                                                                    resource_type,
                                                                                                    self.data)
                LOG.exception(em)
        if self.method == "DELETE":
            self.base_data.timestamp = get_now_time()
            self.base_data.resource_id = self.data.get("resource_id")

    @property
    def post_data(self):
        """return post data"""

        # 构建post数据
        self.base_data.resources = {self.zone + "/" + "volume_size": self.used
                                    }
        # 云磁盘价格目前是以分为单位
        self.base_data.order_type = "2"
        self.base_data.tenant_id = self.user_data.get("project").get("id")
        self.base_data._context_project_name = self.user_data.get("project").get("name")
        self.base_data._context_user_name = self.user_data.get("user").get("name")
        self.base_data.user_id = self.user_data.get("user").get("id")
        order_data = PostData(self.base_data)
        return order_data.post_data

    def create(self):
        return self.create_order(self.post_data, token=self.token)

    def update(self):
        pass

    def delete(self):
        return self.end_order(self.base_data.resource_id, token=self.token)
