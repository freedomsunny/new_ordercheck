# encoding=utf-8
import json
import time
import traceback
from tomorrow import threads

from tornado.options import options
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import order_check.log as logging

LOG = logging.getLogger(__name__)

from order_check.utils import get_http, post_http, put_http, patch_http, \
    delete_http, get_token, get_usermsg_from_keystone


class DataObj(object):
    def __init__(self):
        self.timestamp = ""
        self.resources = {}
        self.resource_id = ""
        self.tenant_id = ""
        self._context_project_name = ""
        self._context_user_name = ""
        self.resource = ""
        self.user_id = ""
        self.order_type = "2"
        self.end_time = ""
        self.resource_from_provider = ""
        self.resource_from = ""
        self.money = ""


class PostData(object):
    def __init__(self, data):
        self.data = data

    @property
    def post_data(self):
        postdata = {"timestamp": self.data.timestamp,
                    "resources": self.data.resources,
                    "resource_id": self.data.resource_id,
                    "tenant_id": self.data.tenant_id,
                    "_context_project_name": self.data._context_project_name,
                    "_context_user_name": self.data._context_user_name,
                    "resource": self.data.resource,
                    "user_id": self.data.user_id,
                    "order_type": self.data.order_type,
                    "end_time": self.data.end_time,
                    "resource_from_provider": self.data.resource_from_provider,
                    "resource_from": self.data.resource_from,
                    "money": self.data.money
                    }
        return postdata


class OrderBase(object):
    def __init__(self):
        self.engine = create_engine(options.sql_connection, pool_recycle=1)
        self.session = sessionmaker(bind=self.engine)()
        self.base_data = DataObj()

    def check_order(self, data):
        url = options.check_url + "?resource_id=%s" % data.token
        res = get_http(url=url,
                       headers={"X-Auth-Token": data.token})
        if res.status_code in [200, 404, 302]:
            LOG.info("Check order resource %s status_code %s" % (data.resource_id, res.status_code))
            return res.status_code
        else:
            LOG.exception("Check order faild status_code:%s, checkurl:%s" % (res.status_code, url))
            # raise ValueError("resource_id: {0}".format(data.get("resource_id")))
            return False

    def create_order(self, data, token="", order_type="xcloud"):
        """order_type:
            - xcloud : 象云平台计费 默认
            - tencent : 腾讯平台计费"""
        url = options.order_url + "/order/orders"
        if order_type == "tencent":
            url = options.order_url + "/order/tencent"
        res = post_http(url=url,
                        data=json.dumps(data),
                        headers={"X-Auth-Token": token})
        if res.status_code == 200:
            LOG.info("Create order success,post data: {0}".format(data))
            return True
        else:
            LOG.exception("Create order faild status_code: %s, orderurl:%s, postdata:%s" %
                          (res.status_code, url, json.dumps(data))
                          )
            return False
            # raise ValueError("resource_id: {0}".format(data.get("resource_id")))

    def end_order(self, resource_id, token="", order_type="xcloud"):
        """order_type:
            - xcloud : 象云平台计费, 默认
            - tencent : 腾讯平台计费"""
        url = options.order_url + "/order/orders" + "/" + resource_id.strip()
        if order_type == "tencent":
            # not define now
            url = options.order_url + "/order/tencent" + "/" + resource_id
        res = delete_http(url=url,
                          headers={"X-Auth-Token": token})
        if res.status_code == 200:
            LOG.info("End order success,resource id %s" % json.dumps(resource_id))
            return True
        else:
            LOG.exception("End order faild status_code: %s,  orderurl:%s, resource id:%s"
                          % (res.status_code, url, resource_id)
                          )
            # raise ValueError("resource_id: {0}".format(data.get("resource_id")))
            return False

    def update_order(self, data, token="", order_type="xcloud"):
        """order_type:
            - xcloud : 象云平台计费, 默认
            - tencent : 腾讯平台计费"""
        url = options.order_url + "/order/orders" + "/" + data.get("resource_id")
        if order_type == "tencent":
            # not define now
            url = options.order_url + "/order/tencent" + "/" + data.get("resource_id")
        res = put_http(url=url,
                       data=json.dumps(data),
                       headers={"X-Auth-Token": token})
        if res.status_code == 200:
            LOG.info("Update order success,post data: {0}".format(data))
            return True
        else:
            LOG.exception("Update order faild status_code: %s, orderurl:%s, postdata:%s" %
                          (res.status_code, url, json.dumps(data))
                          )
            return False

    def user_info(self, token):
        result = get_usermsg_from_keystone(token)
        if not result:
            em = "get user info from keystone error. token: <{0}>".format(token)
            LOG.exception(em)
            raise ValueError(em)
        return result

    def cleanup(self):
        self.session.close()
