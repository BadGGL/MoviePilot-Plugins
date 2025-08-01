import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from croniter import croniter
from datetime import datetime

from app.plugins import _PluginBase
from app.log import logger
from app.core.event import eventmanager, Event


class CustomNotify(_PluginBase):
    plugin_name = "自定义定时通知"
    plugin_desc = "按 cron 定时发送自定义内容到通知渠道"
    plugin_version = "1.1.0"
    plugin_author = "CODEGGL"

    # 配置字段
    _enabled = False
    _cron = "0 9 * * *"
    _message = "早上好！今天是 {now}，祝你开心每一天！"
    _scheduler: AsyncIOScheduler = None

    # -------------------------------------------------
    def init_plugin(self, config: dict = None):
        """配置变更时触发；负责启动/停止调度器"""
        # 1. 读取配置
        if config:
            self._enabled = bool(config.get("enabled"))
            self._cron = str(config.get("cron") or "0 9 * * *")
            self._message = str(config.get("message") or "Hello from MoviePilot!")

        # 2. 先停掉旧调度器
        self.stop_service()

        # 3. 如果启用且表达式合法，则启动
        if self._enabled and croniter.is_valid(self._cron):
            self._scheduler = AsyncIOScheduler()
            self._scheduler.add_job(
                self._send,
                trigger="cron",
                **croniter(self._cron).expressions
            )
            self._scheduler.start()
            logger.info(f"[CustomNotify] 定时任务已启动：{self._cron}")
        elif self._enabled:
            logger.warning("[CustomNotify] cron 表达式非法！")

    # -------------------------------------------------
    async def _send(self):
        """真正发通知的地方"""
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            text = self._message.format(now=now_str)
            self.chain.post_message(
                title="自定义定时通知",
                text=text
            )
            logger.info("[CustomNotify] 通知已发送")
        except Exception as e:
            logger.error(f"[CustomNotify] 发送失败：{e}")

    # -------------------------------------------------
    def get_form(self):
        """返回 Vue 表单配置"""
        return [
            {
                "component": "VSwitch",
                "props": {
                    "model": "enabled",
                    "label": "启用插件"
                }
            },
            {
                "component": "VTextField",
                "props": {
                    "model": "cron",
                    "label": "Cron 表达式",
                    "placeholder": "0 9 * * *"
                }
            },
            {
                "component": "VTextarea",
                "props": {
                    "model": "message",
                    "label": "消息内容",
                    "rows": 4,
                    "placeholder": "支持变量：{now} 会被替换为当前时间"
                }
            }
        ]

    # -------------------------------------------------
    def stop_service(self):
        """禁用或重启时清理调度器"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
            self._scheduler = None
            logger.info("[CustomNotify] 调度器已停止")
