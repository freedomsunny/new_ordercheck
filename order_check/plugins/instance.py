#encoding=utf-8

from order_check.utils import get_now_time
from order_check.options import get_options
from order_check.plugins.manageresource import OrderBase, PostData
import order_check.log as logging


options = get_options()
LOG = logging.getLogger(__name__)


class Instance(OrderBase):
    def __init__(self, data, method, resource_type, token):
        """
        data: the request data(get from redis types string)
        """
        super(Instance, self).__init__()
        self.data = data
        if method == "POST":
            try:
                self.base_data.resource_id = data.get("server").get("id")
            except:
                em = "get data may be not we need. method: {0} resource type: {1} data: {2}".format(method,
                                                                                                    resource_type,
                                                                                                    self.data)
                LOG.exception(em)
        if method == "DELETE":
            self.base_data.resource_id = data.get("resource_id")
        self.resource_type = resource_type
        self.method = method
        self.token = token
        self.user_data = self.user_info(token=token)

    @property
    def get_vm_data(self):
        result = self.session.execute("select uuid, vcpus, memory_mb, root_gb, created_at, deleted_at, vm_state,deleted," \
                                          "user_id, project_id, availability_zone from nova.instances WHERE uuid = \'{0}\'".
                                          format(self.base_data.resource_id)).first()
        if not result:
            return None
        # 云主机是否被删除
        self.base_data.timestamp = str(result[5]) if result[7] else str(result[4])
        if result[10]:
            resources = {
                result[10] + "/" + "vcpus": "" if self.method == "DELETE" else result[1],
                result[10] + "/" + "memory_mb": "" if self.method == "DELETE" else result[2],
                result[10] + "/" + "disk_gb": "" if self.method == "DELETE" else result[3]
            }
        else:
            resources = {
                "vcpus": "" if self.method == "DELETE" else result[1],
                "memory_mb": "" if self.method == "DELETE" else result[2],
                "disk_gb": "" if self.method == "DELETE" else result[3],
            }
        self.base_data.resources = resources
        self.base_data.resource_id = result[0]
        self.base_data.tenant_id = self.user_data.get("project").get("id")
        self.base_data._context_project_name = self.user_data.get("project").get("name")
        self.base_data._context_user_name = self.user_data.get("user").get("name")
        self.base_data.resource = self.resource_type
        self.base_data.user_id = self.user_data.get("user").get("id")
        order_data = PostData(self.base_data)
        return order_data.post_data

    def create(self):
        return self.create_order(self.get_vm_data, token=self.token)

    def update(self):
        pass

    def delete(self):
        return self.end_order(self.base_data.resource_id, token=self.token)


