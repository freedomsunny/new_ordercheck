#encoding=utf-8

from order_check.options import get_options
from order_check.plugins.manageresource import OrderBase, PostData
import order_check.log as logging
from order_check.utils import get_now_time


options = get_options()
LOG = logging.getLogger(__name__)


class FloatingIps(OrderBase):
    def __init__(self, data, method, resource_type, token):
        """
        data: the request data(get from redis types string)
        """
        super(FloatingIps, self).__init__()
        self.data = data
        self.method = method
        self.token = token
        self.resource_type = resource_type
        if self.method == "POST" or self.method == "PUT":
            try:
                self.ip_address = self.data.get("floatingip").get("floating_ip_address")
                self.base_data.resource_id = self.data.get("floatingip").get("id")
            except:
                em = "get data may be not we need. method: {0} resource type: {1} data: {2}".format(method,
                                                                                                    resource_type,
                                                                                                    self.data)
                LOG.exception(em)
        elif self.method == "DELETE":
            self.base_data.resource_id = self.data.get("resource_id")
        self.user_data = self.user_info(token=token)

    @property
    def floating_ip_data(self):
        # 获取带宽
        band_width_kbps = 1024
        # 获取端口ID
        floating_ip = self.session.execute("select * from neutron.floatingips where id = \'{0}\'".format(self.base_data.resource_id)).first()
        if not floating_ip:
            em = "can not found floating ip. <{0}>".format(self.base_data.resource_id)
            LOG.exception(em)
            return {}
        port_id = floating_ip[4]
        # 获取带宽与端口绑定的策略
        policy_bindings = self.session.execute("select * from neutron.qos_port_policy_bindings where port_id = \'{0}\'".format(port_id)).first()
        if policy_bindings:
            policy_id = policy_bindings[1]

            bandwidth = self.session.execute("select * from neutron.qos_bandwidth_limit_rules where qos_policy_id = \'{0}\'".format(policy_id)).first()
            if bandwidth:
                band_width_kbps = bandwidth[2]
        # 返回data
        self.base_data.resources = {"floating_ip": 1,
                                    "max_kbps": band_width_kbps
                                    }
        self.base_data.timestamp = get_now_time()
        self.base_data.tenant_id = self.user_data.get("project").get("id")
        self.base_data._context_project_name = self.user_data.get("project").get("name")
        self.base_data._context_user_name = self.user_data.get("user").get("name")
        self.base_data.user_id = self.user_data.get("user").get("id")
        self.base_data.resource = self.ip_address
        self.base_data.order_type = "2"
        order_data = PostData(self.base_data)
        return order_data.post_data

    def create(self):
        return self.create_order(self.floating_ip_data, token=self.token)

    def update(self):
        pass

    def delete(self):
        return self.end_order(self.base_data.resource_id, token=self.token)


