#encoding=utf-8

import time
from order_check.options import get_options
from order_check.plugins.manageresource import OrderBase, PostData
import order_check.log as logging
from order_check.utils import get_now_time



options = get_options()
LOG = logging.getLogger(__name__)


class Routers(OrderBase):
    def __init__(self, data, method, resource_type, token):
        """
        data: the request data(get from redis types dict)
        """
        super(Routers, self).__init__()
        self.data = data
        # the router id is `resource_id`
        self.resource_type = resource_type
        self.method = method
        self.token = token
        self.user_data = self.user_info(token=token)
        if self.method == "POST" or self.method == "PUT":
            try:
                self.base_data.resource_id = self.data.get("router").get("id")
                self.ip_address = data.get("router"). \
                    get('external_gateway_info'). \
                    get("external_fixed_ips")[0]. \
                    get("ip_address")
            except:
                em = "get data may be not we need. method: {0} resource type: {1} data: {2}".format(method,
                                                                                                    resource_type,
                                                                                                    self.data)
                LOG.exception(em)
        elif self.method == "DELETE":
            self.base_data.resource_id = self.data.get("resource_id")

    @property
    def router_info(self):
        # 根据路由ID找到port id
        router = self.session.execute("select * from neutron.routers where id = \'{0}\'".format(self.base_data.resource_id)).first()
        if not router:
            em = "can not get router info. router id: <{0}>".format(self.base_data.resource_id)
            LOG.exception(em)
            return False
        port_id = router[5]
        # 默认带宽为1024kb，如果没有找到则用默认
        band_width = 1024
        # 根据`port_id`查找策略ID
        policy = self.session.execute("select * from neutron.qos_port_policy_bindings where port_id = \'{0}\'".format(port_id)).first()
        if policy:
            policy_id = policy[0]
            # 根据策略ID最终找到带宽
            bandwidth = self.session.execute("select * from neutron.qos_bandwidth_limit_rules where qos_policy_id = \'{0}\'".format(policy_id)).first()
            if bandwidth:
                band_width = bandwidth[2]

        self.base_data.resources = {"floating_ip": 1,
                                    "max_kbps": band_width
                                    }
        self.base_data.timestamp = get_now_time()
        self.base_data.order_type = "2"
        self.base_data.tenant_id = self.user_data.get("project").get("id")
        self.base_data._context_project_name = self.user_data.get("project").get("name")
        self.base_data._context_user_name = self.user_data.get("user").get("name")
        self.base_data.user_id = self.user_data.get("user").get("id")
        self.base_data.resource = self.ip_address
        order_data = PostData(self.base_data)
        return order_data.post_data

    def create(self):
        return self.create_order(self.router_info, token=self.token)

    def update(self):
        pass

    def delete(self):
        return self.end_order(self.base_data.resource_id, token=self.token)


