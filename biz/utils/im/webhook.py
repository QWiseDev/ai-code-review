import requests
import os

from biz.service.review_service import ReviewService
from biz.utils.log import logger


class ExtraWebhookNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化ExtraWebhook通知器
        :param webhook_url: 自定义webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('EXTRA_WEBHOOK_URL', '')
        self.enabled = os.environ.get('EXTRA_WEBHOOK_ENABLED', '0') == '1'

    def send_message(self, system_data: dict, webhook_data: dict):
        """
        发送额外自定义webhook消息
        :param system_data: 系统消息内容
        :param webhook_data: github、gitlab的push event、merge event的原始数据
        """
        if not self.enabled:
            logger.info("ExtraWebhook推送未启用")
            return

        try:
            raw_project_name = system_data.get("project_name") if system_data else None
            raw_url_slug = system_data.get("url_slug") if system_data else None
            normalized_project_name = (raw_project_name or '').strip() or None
            normalized_url_slug = (raw_url_slug or '').strip() or None
            project_config = ReviewService.get_effective_project_webhook_config(
                project_name=normalized_project_name,
                url_slug=normalized_url_slug
            )
            identifier = normalized_project_name or normalized_url_slug or "unknown"

            if project_config:
                if not project_config.get('extra_webhook_enabled'):
                    logger.info(f"项目 {identifier} 未启用自定义Webhook推送，跳过发送。")
                    return
                target_url = (project_config.get('extra_webhook_url') or '').strip()
                if not target_url:
                    logger.warning(f"项目 {identifier} 已启用自定义Webhook推送但未配置 webhook 地址，跳过发送。")
                    return
            else:
                target_url = self.default_webhook_url

            if not target_url:
                logger.info("未找到可用的自定义Webhook地址，跳过发送。")
                return

            data = {
                "ai_codereview_data": system_data,
                "webhook_data": webhook_data
            }
            response = requests.post(
                url=target_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
                logger.error(f"ExtraWebhook消息发送失败! webhook_url:{target_url}, error_msg:{response.text}")
                return

        except Exception as e:
            logger.error(f"ExtraWebhook消息发送失败! ", e)
