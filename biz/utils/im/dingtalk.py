import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse

import requests

from biz.service.review_service import ReviewService

from biz.utils.log import logger


class DingTalkNotifier:
    def __init__(self, webhook_url=None):
        self.enabled = os.environ.get('DINGTALK_ENABLED', '0') == '1'
        self.default_webhook_url = webhook_url or os.environ.get('DINGTALK_WEBHOOK_URL')

    def _get_project_config(self, project_name=None, url_slug=None):
        """从数据库获取项目 webhook 配置"""
        normalized_project_name = (project_name or '').strip() or None
        normalized_url_slug = (url_slug or '').strip() or None
        return ReviewService.get_effective_project_webhook_config(
            project_name=normalized_project_name,
            url_slug=normalized_url_slug
        )

    def _get_webhook_url(self, project_name=None, url_slug=None):
        """
        从环境变量获取项目对应的 Webhook URL（兼容旧方案）
        :param project_name: 项目名称
        :param url_slug: 由 gitlab 项目的 url 转换而来的 slug
        :return: Webhook URL
        :raises ValueError: 如果未找到 Webhook URL
        """
        # 如果未提供 project_name，直接返回默认的 Webhook URL
        if not project_name:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称，且未设置默认的钉钉 Webhook URL。")

        # 构造目标键
        target_key_project = f"DINGTALK_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"DINGTALK_WEBHOOK_URL_{url_slug.upper()}"

        # 遍历环境变量
        for env_key, env_value in os.environ.items():
            env_key_upper = env_key.upper()
            if env_key_upper == target_key_project:
                return env_value  # 找到项目名称对应的 Webhook URL，直接返回
            if env_key_upper == target_key_url_slug:
                return env_value  # 找到 GitLab URL 对应的 Webhook URL，直接返回

        # 如果未找到匹配的环境变量，降级使用全局的 Webhook URL
        if self.default_webhook_url:
            return self.default_webhook_url

        # 如果既未找到匹配项，也没有默认值，抛出异常
        raise ValueError(f"未找到项目 '{project_name}' 对应的钉钉Webhook URL，且未设置默认的 Webhook URL。")

    def send_message(self, content: str, msg_type='text', title='通知', is_at_all=False, project_name=None, url_slug = None):
        if not self.enabled:
            logger.info("钉钉推送未启用")
            return

        try:
            project_config = self._get_project_config(project_name=project_name, url_slug=url_slug)
            identifier = (project_name or '').strip() or (url_slug or '').strip() or "unknown"
            if project_config:
                if not project_config.get('dingtalk_enabled'):
                    logger.info(f"项目 {identifier} 未启用钉钉推送，跳过发送。")
                    return
                post_url = (project_config.get('dingtalk_webhook_url') or '').strip()
                if not post_url:
                    logger.warning(f"项目 {identifier} 已启用钉钉推送但未配置 webhook 地址，跳过发送。")
                    return
            else:
                post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)

            headers = {
                "Content-Type": "application/json",
                "Charset": "UTF-8"
            }
            content = content.replace("https://gitserver.gisinfo.com/", "https://gitserver.gisinfo.com:8443/")
            if msg_type == 'markdown':
                message = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title,  # Customize as needed
                        "text": content
                    },
                    "at": {
                        "isAtAll": is_at_all
                    }
                }
            else:
                message = {
                    "msgtype": "text",
                    "text": {
                        "content": content
                    },
                    "at": {
                        "isAtAll": is_at_all
                    }
                }
            response = requests.post(url=post_url, data=json.dumps(message), headers=headers)
            response_data = response.json()
            if response_data.get('errmsg') == 'ok':
                logger.info(f"钉钉消息发送成功! webhook_url:{post_url}")
            else:
                logger.error(f"钉钉消息发送失败! webhook_url:{post_url},errmsg:{response_data.get('errmsg')}")
        except Exception as e:
            logger.error(f"钉钉消息发送失败! ", e)
