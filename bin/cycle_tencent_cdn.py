#encoding=utf-8
import sys
sys.path.append("/root/new_ordercheck")
import time
from order_check.plugins.cdn_tencent import TencentCDN
import order_check.log as logging
from order_check.options import get_options
from order_check.utils import get_token, get_http, post_http
from tomorrow import threads


options = get_options()
LOG = logging.getLogger(__name__)

@threads(10)
def send_cdn_order(user_id):
    cdn_obj = TencentCDN(user_id=user_id)
    cdn_obj.create()


if __name__ == "__main__":
    run_time = ["23:50"]
    while True:
        now_time = time.strftime('%H:%M', time.localtime(time.time()))
        if now_time in run_time:
            # 获取所有用户
            url = "{0}/cloud/tencent/user".format(options.api_gateway_url)
            admin_token = get_token()
            if not admin_token:
                em = "get token error...."
                LOG.exception(em)
                time.sleep(5)
                continue
            headers = {"X-Auth-Token": admin_token}
            users = get_http(url=url, headers=headers).json()["data"]
            for user_id in users:
                send_cdn_order(user_id=user_id)
        time.sleep(5)
