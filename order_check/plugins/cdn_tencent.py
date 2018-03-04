# encoding=utf-8
import json
import cPickle

from order_check.options import get_options
from order_check.plugins.manageresource import OrderBase, PostData
from order_check.utils import get_http, post_http, getDateTimeFromISO8601String, get_token, get_today, get_month_day1, \
    get_Ndays_ago
from order_check.cache import Backend
import order_check.log as logging
from order_check.exception import *

options = get_options()
LOG = logging.getLogger(__name__)


class TencentCDN(OrderBase):
    """腾迅CDN计费"""

    def __init__(self, user_id):
        super(TencentCDN, self).__init__()
        self.user_id = user_id
        self.today = get_today()
        self.month_day1 = get_month_day1()
        self.cache = Backend()
        self.resource_type = "cdn_tencent"
        self.admin_token = get_token()
        if not self.admin_token:
            raise ValueError("Error get admin token error")
        self.headers = {"X-Auth-Token": self.admin_token,
                        "Content-Type": "application/json",
                        "TxToken": self.tencent_user_token.get("TxToken", ""),
                        "TxKey": self.tencent_user_token.get("TxKey", ""),
                        "TxId": self.tencent_user_token.get("TxId", "")
                        }

    @property
    def tencent_user_token(self):
        key = "tencent_token" + self.user_id
        result = self.cache.get(key)
        if not result:
            url = "{0}/cloud/tencent/token/{1}".format(options.api_gateway_url, self.user_id)
            headers = {"X-Auth-Token": self.admin_token}
            result = get_http(url=url, headers=headers).json()["data"]
            if not result:
                return {}
            self.cache.set(id=key, user_msg=cPickle.dumps(result), timeout=300)
            return result

        return cPickle.loads(result)

    def _tencent_cdn(self):
        """获取用户所有使用cdn的域名"""
        result = []
        url = "{0}/cloud/tencent/cdndomain".format(options.api_gateway_url)
        domains = get_http(url=url, headers=self.headers).json()["data"]
        for domain in domains:
            result.append(domain.get("domain"))
        return result

    def _cdn_sum_flow(self, domains, start_time, end_time):
        """
        获取某个域某个时间段的cdn流量总和
        domain: www.gagaga.com
        start_time: 2016-05-03
        end_time: 2016-05-03
        """
        url = "{0}/cloud/tencent/cdnsumflow".format(options.api_gateway_url)
        data = {
            "domain": domains,
            "start_time": start_time,
            "end_time": end_time,
        }
        result = post_http(url=url, headers=self.headers, data=json.dumps(data)).json()["data"]
        if not result:
            return 0
        # unit Bytes
        return result

    @property
    def keystone_user_data(self):
        user = self.session.execute("select * from keystone.local_user where user_id = '{0}'". \
                                    format(self.user_id)).first()
        if not user:
            em = "can not found user <{0}> from keystone".format(self.user_id)
            LOG.exception(em)
            return {}
        # 项目分配表
        project_assignment = self.session.execute("select * from keystone.assignment where actor_id = '{0}'". \
                                                  format(self.user_id)).first()
        if not project_assignment:
            em = "can not found user's <{0}> project".format(self.user_id)
            LOG.exception(em)
            return {}
        # 项目
        project = self.session.execute("select * from keystone.project where id = '{0}'". \
                                       format(project_assignment[2])).first()
        if not project:
            em = "can not found project <{0}>".format(project_assignment[2])
            LOG.exception(em)
            return {}
        return {"project_id": project[0],
                "project_name": project[1],
                "user_name": user[3]
                }

    @property
    def cdn_flow_price(self):
        domains = self._tencent_cdn()
        total_flow_day = 0
        total_flow_month = 0
        if domains:
            # 获取单个域名当天流量
            flow_Bytes_day = self._cdn_sum_flow(domains=domains, start_time=self.today, end_time=self.today)
            # 获取单个域名当月流量(每月1号到当前)
            flow_Bytes_month = self._cdn_sum_flow(domains=domains, start_time=self.month_day1, end_time=self.today)
            # 获取单个域名当月流量
            total_flow_day += flow_Bytes_day
            total_flow_month += flow_Bytes_month
        if total_flow_day <= 0:
            return 0
        ############阶梯价格#################
        #               元/GB
        # 0GB-2TB	    0.23
        # 2TB-10TB	    0.22
        # 10TB-50TB	    0.21
        # 50TB-100TB	0.19
        # 大于等于 100TB 低于 0.14
        #####################################

        # 阶梯计费
        # 大于2TB小于10TB
        if total_flow_month <= 10000000000 and total_flow_month >= 2000000000:
            money = self.expr_price(total_flow_month=total_flow_month,
                                    total_flow_day=total_flow_day,
                                    min_flow=2000000000,
                                    low_price=0.23,
                                    hight_price=0.22)
        # 大于10TB小于50TB
        elif total_flow_month <= 50000000000 and total_flow_month >= 10000000000:
            money = self.expr_price(total_flow_month=total_flow_month,
                                    total_flow_day=total_flow_day,
                                    min_flow=10000000000,
                                    low_price=0.22,
                                    hight_price=0.21)
        # 大于50TB小于100TB
        elif total_flow_month <= 100000000000 and total_flow_month >= 100000000000:
            money = self.expr_price(total_flow_month=total_flow_month,
                                    total_flow_day=total_flow_day,
                                    min_flow=100000000000,
                                    low_price=0.21,
                                    hight_price=0.19)
        # 大于100TB
        elif total_flow_month >= 100000000000:
            money = self.expr_price(total_flow_month=total_flow_month,
                                    total_flow_day=total_flow_day,
                                    min_flow=100000000000,
                                    low_price=0.19,
                                    hight_price=0.14)
        # 小于2TB
        else:
            money = (total_flow_day / 1024.0 / 1024) * 0.23

        return {"money": money,
                "total_flow_day": total_flow_day,
                "total_flow_month": total_flow_month
                }

    @property
    def post_data(self):
        self.base_data.resources = {"tencent_cdn": self.cdn_flow_price.get("total_flow_day")
                                    }
        self.base_data.timestamp = self.today + " 00:00:00"
        self.base_data.end_time = self.today + " 23:59:59"
        # 云磁盘价格目前是以分为单位
        self.base_data.money = self.cdn_flow_price.get("money")
        self.base_data.resource_from_provider = "tencent"
        self.base_data.resource = "tencent_cdn"
        self.base_data.order_type = "2"
        self.base_data.resource = self.resource_type
        # user about
        self.base_data.tenant_id = self.keystone_user_data.get("project_id")
        self.base_data._context_project_name = self.keystone_user_data.get("project_name")
        self.base_data._context_user_name = self.keystone_user_data.get("user_name")
        self.base_data.user_id = self.user_id
        order_data = PostData(self.base_data)
        return order_data.post_data

    def expr_price(self, total_flow_month, total_flow_day, min_flow, low_price, hight_price):
        surplus = total_flow_month - min_flow
        if surplus > 0:
            money = ((surplus / 1024.0 / 1024) * hight_price) + (((total_flow_day - surplus) / 1024.0 / 1024) * low_price)
        else:
            money = (total_flow_day / 1024.0 / 1024) * low_price
        return money

    def create(self):
        return self.create_order(self.post_data, token=self.admin_token, order_type="tencent")

    def update(self):
        pass

    def delete(self):
        pass
        # return self.end_order(self.base_data.resource_id, order_type="tencent")
