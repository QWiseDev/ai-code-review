import json
from typing import Optional

import requests

from biz.utils.log import logger


class TeamWebhookNotifier:
    """团队级Webhook发送工具"""

    @staticmethod
    def send_markdown(webhook_url: Optional[str], title: Optional[str], content: str) -> bool:
        """发送 Markdown 格式的团队工作日报"""
        normalized_url = (webhook_url or '').strip()
        if not normalized_url:
            logger.warning("团队Webhook地址为空，跳过发送。")
            return False

        markdown_text = content if isinstance(content, str) else str(content or '')
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title or "团队工作日报",
                "text": markdown_text
            }
        }
        headers = {
            "Content-Type": "application/json",
            "Charset": "UTF-8"
        }

        try:
            response = requests.post(url=normalized_url, data=json.dumps(payload), headers=headers, timeout=10)
            if response.status_code != 200:
                logger.error("团队Webhook推送失败，状态码：%s，响应：%s", response.status_code, response.text)
                return False

            try:
                response_json = response.json()
                if isinstance(response_json, dict):
                    errcode = response_json.get('errcode')
                    errmsg = response_json.get('errmsg')
                    if errcode not in (None, 0):
                        logger.error("团队Webhook推送失败，errcode=%s, errmsg=%s", errcode, errmsg)
                        return False
            except ValueError:
                # 非 JSON 响应，视为第三方已接受
                pass

            logger.info("团队[%s]日报推送成功。", title or "未命名团队")
            return True
        except requests.RequestException as e:
            logger.error("团队Webhook推送异常：%s", e)
            return False
