import logging
import os

import telepot
from distribrewed_core.base.worker import BaseWorker

log = logging.getLogger(__name__)


class TelegramWorker(BaseWorker):
    def __init__(self):
        super(TelegramWorker, self).__init__()
        token = os.environ.get('TELEGRAM_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT')
        if token is None:
            log.error('Provide a bot token for telegram in env variable \'TELEGRAM_TOKEN\'')
            exit(0)
        if self.chat_id is None:
            log.error('Provide a chat id for telegram in env variable \'TELEGRAM_CHAT\'')
            exit(0)
        self.bot = telepot.Bot(token)

    def _worker_info(self):
        base = super(TelegramWorker, self)._worker_info()
        bot_info = self.bot.getMe()
        bot_info['telegram_id'] = bot_info.pop('id')
        return {**base, **bot_info}

    def send_message(self, message):
        self.bot.sendMessage(self.chat_id, message)


if __name__ == "__main__":
    worker = TelegramWorker()
    worker.send_message('Whoop Whoop')
