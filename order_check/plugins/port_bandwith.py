#encoding=utf-8

import time
from order_check.options import get_options
from order_check.plugins.manageresource import OrderBase, PostData
import order_check.log as logging
from order_check.utils import get_now_time


##############################################
#
# 用户更新带宽时，需要计费。更新带宽时是对port操作
#
###############################################

options = get_options()
LOG = logging.getLogger(__name__)


class PortBandWith(OrderBase):
    def __init__(self, data, method, resource_type, token):
        """
        data: the request data(get from redis types dict)
        """
        super(PortBandWith, self).__init__()
        self.data = data
        self.resource_type = resource_type
        self.method = method
        self.token = token
        self.user_data = self.user_info(token=token)
        if self.method == "PUT":
            try:
                # floating ip 端口ID
                self.port_id = self.data.get("port").get('id')
                # ip address is the resource
                self.base_data.resource = data.get("port").get("fixed_ips")[0].get("ip_address")
                # policy id to found bandwith used
                self.qos_policy_id = self.data.get("port").get('qos_policy_id')
            except:
                em = "get data may be not we need. method: {0} resource type: {1} data: {2}".format(method,
                                                                                                    resource_type,
                                                                                                    self.data)
                LOG.exception(em)

    @property
    def bandwith_info(self):
        # 默认带宽为1024kb
        band_width_kbps = 1024
        bandwidth = self.session.execute("select * from neutron.qos_bandwidth_limit_rules where qos_policy_id = \'{0}\'".format(self.qos_policy_id)).first()
        if bandwidth:
            band_width_kbps = bandwidth[2]
        # 得到资源ID
        floating_id = self.session.execute("select * from neutron.floatingips where floating_port_id = \'{0}\'".format(self.port_id)).first()
        self.base_data.resource_id = floating_id[1]
        self.base_data.resources = {"max_kbps": band_width_kbps
                                    }
        self.base_data.timestamp = get_now_time()
        self.base_data.order_type = "2"
        self.base_data.tenant_id = self.user_data.get("project").get("id")
        self.base_data._context_project_name = self.user_data.get("project").get("name")
        self.base_data._context_user_name = self.user_data.get("user").get("name")
        self.base_data.user_id = self.user_data.get("user").get("id")
        self.base_data.resource = self.resource_type
        order_data = PostData(self.base_data)
        return order_data.post_data

    def create(self):
        pass

    def update(self):
        return self.update_order(self.bandwith_info, token=self.token)

    def delete(self):
        pass

