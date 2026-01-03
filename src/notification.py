"""
通知服務模組

提供多種通知管道整合，實現：
- Line Notify 推播
- Telegram Bot 推播
- 重試機制與錯誤處理

參考：docs/Implementation.md 第 4.3 節
"""

import logging
import time
import requests


class NotificationService:
    """
    通知服務

    設計模式：Facade Pattern (為多種通知管道提供統一接口)
    支援多種通知管道：Line Notify, Telegram Bot

    Attributes:
        config (dict): 配置字典，包含 Token 等設定

    Examples:
        >>> service = NotificationService(config)
        >>> service.send_line_notify("選股完成")
    """

    def __init__(self, config: dict):
        """
        初始化通知服務

        Args:
            config: 配置字典，包含 Token 等設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def send_line_notify(
        self,
        message: str,
        max_retries: int = 3
    ) -> bool:
        """
        發送 Line Notify 通知
        """
        token = self.config.get('line_notify', {}).get('token')
        if not token:
            self.logger.warning("未配置 Line Notify Token")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        payload = {"message": message}
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://notify-api.line.me/api/notify",
                    headers=headers,
                    params=payload,
                    timeout=10
                )
                if response.status_code == 200:
                    self.logger.info("Line Notify 發送成功")
                    return True
                else:
                    self.logger.error(f"Line Notify 失敗: {response.text}", exc_info=True)
            except Exception as e:
                self.logger.warning(f"Line Notify 嘗試 {attempt+1} 失敗: {e}")
                time.sleep(2)
        return False

    def send_telegram(
        self,
        message: str,
        chat_id: str = None
    ) -> bool:
        """
        發送 Telegram Bot 通知
        """
        token = self.config.get('telegram', {}).get('bot_token')
        target_chat_id = chat_id or self.config.get('telegram', {}).get('chat_id')
        
        if not token or not target_chat_id:
            self.logger.warning("未配置 Telegram Bot Token 或 Chat ID")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info("Telegram 訊息發送成功")
                return True
            else:
                self.logger.error(f"Telegram 失敗: {response.text}", exc_info=True)
                return False
        except Exception as e:
            self.logger.error(f"Telegram 發送異常: {e}", exc_info=True)
            return False



if __name__ == '__main__':
    print("NotificationService 模組已載入")
